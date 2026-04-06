import os
import smtplib
import threading
import time
import secrets
from flask import Blueprint, current_app, render_template, redirect, url_for, request, jsonify, flash, send_file
from email.message import EmailMessage
from flask_login import login_user, logout_user, login_required, current_user
from app import db
from app.models import User, API, APILog, Alert, PasswordResetCode
from datetime import datetime, timedelta
from pathlib import Path
import csv
from io import StringIO, BytesIO
import requests
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak, Image
from reportlab.lib.units import inch
from sqlalchemy.exc import IntegrityError

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')
main_bp = Blueprint('main', __name__)
PROJECT_ROOT = Path(__file__).resolve().parent.parent


def send_password_reset_email(user, code):
    """Send password reset code to the user's registered email."""
    from flask import current_app

    if current_app.config.get("MAIL_SUPPRESS_SEND", False):
        return True

    mail_server = current_app.config.get("MAIL_SERVER")
    mail_username = current_app.config.get("MAIL_USERNAME")
    mail_password = current_app.config.get("MAIL_PASSWORD")
    sender = current_app.config.get("MAIL_DEFAULT_SENDER")

    if not all([mail_server, mail_username, mail_password, sender]):
        return False

    message = EmailMessage()
    message["Subject"] = "API Monitor Password Reset Code"
    message["From"] = sender
    message["To"] = user.email
    message.set_content(
        f"Hello {user.username},\n\n"
        f"Your password reset code is: {code}\n\n"
        f"This code will expire in {current_app.config.get('PASSWORD_RESET_EXPIRY_MINUTES', 10)} minutes.\n"
        "If you did not request a password reset, you can ignore this email.\n"
    )

    with smtplib.SMTP(mail_server, current_app.config.get("MAIL_PORT", 587)) as smtp:
        if current_app.config.get("MAIL_USE_TLS", True):
            smtp.starttls()
        smtp.login(mail_username, mail_password)
        smtp.send_message(message)
    return True


def can_show_reset_code():
    """Allow showing reset codes locally when email is not configured."""
    return current_app.config.get("DEV_SHOW_RESET_CODE", True)

# ==================== AUTHENTICATION ====================

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password')
        
        if User.query.filter_by(username=username).first():
            flash('Username already exists', 'danger')
            return redirect(url_for('auth.register'))
        if User.query.filter_by(email=email).first():
            flash('Email is already registered. Please login or use forgot password.', 'danger')
            return redirect(url_for('auth.register'))
        
        user = User(username=username, email=email)
        user.set_password(password)
        db.session.add(user)
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            flash('Username or email already exists. Please use different details.', 'danger')
            return redirect(url_for('auth.register'))
        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('auth.login'))
    
    return render_template('register.html')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('main.dashboard'))
        
        flash('Invalid username or password', 'danger')
    
    return render_template('login.html')


@auth_bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        user = User.query.filter_by(email=email).first()

        if user:
            PasswordResetCode.query.filter_by(user_id=user.id, used=False).update({'used': True}, synchronize_session=False)
            code = f"{secrets.randbelow(900000) + 100000}"
            expiry_minutes = current_app.config.get("PASSWORD_RESET_EXPIRY_MINUTES", 10)
            reset_code = PasswordResetCode(
                user_id=user.id,
                code=code,
                expires_at=datetime.utcnow() + timedelta(minutes=expiry_minutes)
            )
            db.session.add(reset_code)
            db.session.commit()

            if send_password_reset_email(user, code):
                flash('A reset code has been sent to your registered email.', 'success')
            else:
                if can_show_reset_code():
                    flash(f'Email is not configured. Use this reset code for now: {code}', 'warning')
                else:
                    flash('Email sending is not configured yet. Set SMTP environment variables and try again.', 'warning')
        else:
            flash('If that email is registered, a reset code has been sent.', 'info')

        return redirect(url_for('auth.reset_password', email=email))

    return render_template('forgot_password.html')


@auth_bp.route('/reset-password', methods=['GET', 'POST'])
def reset_password():
    email = request.values.get('email', '').strip().lower()

    if request.method == 'POST':
        code = request.form.get('code', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')

        user = User.query.filter_by(email=email).first()
        if not user:
            flash('Invalid email or reset code.', 'danger')
            return redirect(url_for('auth.reset_password', email=email))

        reset_code = PasswordResetCode.query.filter_by(
            user_id=user.id,
            code=code,
            used=False
        ).order_by(PasswordResetCode.created_at.desc()).first()

        if not reset_code or not reset_code.is_valid():
            flash('Invalid or expired reset code.', 'danger')
            return redirect(url_for('auth.reset_password', email=email))

        if password != confirm_password:
            flash('Passwords do not match.', 'danger')
            return redirect(url_for('auth.reset_password', email=email))

        if len(password) < 6:
            flash('Password must be at least 6 characters long.', 'danger')
            return redirect(url_for('auth.reset_password', email=email))

        user.set_password(password)
        reset_code.used = True
        PasswordResetCode.query.filter(
            PasswordResetCode.user_id == user.id,
            PasswordResetCode.id != reset_code.id
        ).update({'used': True}, synchronize_session=False)
        db.session.commit()
        flash('Password changed successfully. Please login.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('reset_password.html', email=email)

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('main.index'))

# ==================== MAIN PAGES ====================

@main_bp.route('/')
def index():
    return redirect(url_for('auth.login'))

@main_bp.route('/dashboard')
@login_required
def dashboard():
    apis = API.query.filter_by(user_id=current_user.id).all()
    api_data = []
    
    for api in apis:
        log = api.get_last_log()
        avg_response = api.get_avg_response_time()
        
        # Determine status more accurately
        if not log:
            status = 'Pending'
            status_class = 'warning'
        elif log.status_code == 200:
            status = 'Active'
            status_class = 'success'
        else:
            status = 'Down'
            status_class = 'danger'
        
        api_data.append({
            'id': api.id,
            'name': api.name,
            'url': api.url,
            'status': status,
            'status_class': status_class,
            'response_time': f"{log.response_time:.0f}ms" if log and log.response_time else 'N/A',
            'avg_response_time': f"{avg_response:.0f}ms" if avg_response > 0 else 'N/A',
            'last_checked': log.timestamp.strftime('%Y-%m-%d %H:%M:%S') if log else 'Never',
            'status_code': log.status_code if log else 'N/A'
        })
    
    return render_template('dashboard.html', apis=api_data)

@main_bp.route('/analytics')
@login_required
def analytics():
    apis = API.query.filter_by(user_id=current_user.id).all()
    return render_template('analytics.html', apis=apis)

@main_bp.route('/alerts')
@login_required
def alerts():
    return render_template('alerts.html')


def run_single_api_check(api_id):
    """Run one API check asynchronously so the add flow returns immediately."""
    try:
        api = API.query.get(api_id)
        if not api:
            return

        start_time = time.time()
        try:
            response = requests.get(api.url, timeout=10, allow_redirects=True)
            response_time = (time.time() - start_time) * 1000
            log = APILog(
                api_id=api.id,
                status_code=response.status_code,
                response_time=response_time,
                is_success=(response.status_code == 200),
                timestamp=datetime.utcnow()
            )
        except requests.exceptions.Timeout:
            log = APILog(
                api_id=api.id,
                status_code=0,
                response_time=None,
                is_success=False,
                error_message="Request timeout",
                timestamp=datetime.utcnow()
            )
        except requests.exceptions.ConnectionError:
            log = APILog(
                api_id=api.id,
                status_code=None,
                response_time=None,
                is_success=False,
                error_message="Connection error",
                timestamp=datetime.utcnow()
            )
        except Exception as exc:
            log = APILog(
                api_id=api.id,
                status_code=None,
                response_time=None,
                is_success=False,
                error_message=str(exc)[:500],
                timestamp=datetime.utcnow()
            )

        db.session.add(log)
        db.session.commit()
        generate_alerts_for_api(api)
    except Exception:
        db.session.rollback()


def count_active_alerts(user_id):
    """Return active alert count for a user."""
    return Alert.query.join(API).filter(
        API.user_id == user_id,
        Alert.is_active == True
    ).count()

@main_bp.route('/devops')
@login_required
def devops():
    """DevOps dashboard page"""
    grafana_url = os.environ.get("GRAFANA_URL", "http://localhost:3000")
    prometheus_url = os.environ.get("PROMETHEUS_URL", "http://localhost:9090")
    return render_template('devops.html', grafana_url=grafana_url, prometheus_url=prometheus_url)

@main_bp.route('/csv')
@login_required
def csv_page():
    """Display CSV data in a table"""
    apis = API.query.filter_by(user_id=current_user.id).all()
    csv_data = []
    
    for api in apis:
        logs = APILog.query.filter_by(api_id=api.id).order_by(APILog.timestamp.desc()).limit(100).all()
        for log in logs:
            csv_data.append({
                'api_name': api.name,
                'url': api.url,
                'status_code': log.status_code or 'N/A',
                'response_time': f"{log.response_time:.0f}ms" if log.response_time else 'N/A',
                'timestamp': log.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                'status': 'Success' if log.status_code == 200 else 'Failed'
            })
    
    return render_template('csv_data.html', csv_data=csv_data, total=len(csv_data))

@main_bp.route('/export-csv')
@login_required
def export_csv():
    apis = API.query.filter_by(user_id=current_user.id).all()
    
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(['API Name', 'URL', 'Status Code', 'Response Time (ms)', 'Timestamp'])
    
    for api in apis:
        logs = APILog.query.filter_by(api_id=api.id).order_by(APILog.timestamp.desc()).limit(100).all()
        for log in logs:
            writer.writerow([
                api.name,
                api.url,
                log.status_code or 'N/A',
                log.response_time or 'N/A',
                log.timestamp.strftime('%Y-%m-%d %H:%M:%S')
            ])
    
    return output.getvalue(), 200, {'Content-Disposition': 'attachment; filename=api_monitor.csv', 'Content-Type': 'text/csv'}

# ==================== API ENDPOINTS ====================

@main_bp.route('/api/add', methods=['POST'])
@login_required
def add_api():
    name = request.form.get('name')
    url = request.form.get('url')
    interval = request.form.get('interval', 60, type=int)
    
    api = API(name=name, url=url, user_id=current_user.id, interval=interval)
    db.session.add(api)
    db.session.commit()

    # Run the first check asynchronously so the API card appears immediately.
    from flask import current_app
    app = current_app._get_current_object()

    if not app.config.get("TESTING", False):
        def background_initial_check():
            with app.app_context():
                run_single_api_check(api.id)

        threading.Thread(target=background_initial_check, daemon=True).start()

    flash(f'API "{name}" added successfully!', 'success')
    return redirect(url_for('main.dashboard'))

@main_bp.route('/api/delete/<int:api_id>', methods=['POST'])
@login_required
def delete_api(api_id):
    api = API.query.get_or_404(api_id)
    if api.user_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403
    
    db.session.delete(api)
    db.session.commit()
    flash('API deleted successfully!', 'success')
    return redirect(url_for('main.dashboard'))

# ALL ENDPOINTS MUST COME BEFORE SPECIFIC ID ENDPOINTS
@main_bp.route('/api/chart-data/all')
@login_required
def get_all_chart_data():
    """Get chart data for all user's APIs - each API as separate dataset"""
    hours = request.args.get('hours', 24, type=int)
    chart_type = request.args.get('type', 'line')  # line, bar, pie, area
    cutoff = datetime.utcnow() - timedelta(hours=hours)
    
    # Get all APIs for current user
    apis = API.query.filter_by(user_id=current_user.id).all()
    
    if not apis:
        return jsonify({
            'labels': [],
            'datasets': [],
            'chart_type': chart_type
        })
    
    # Prepare colors for different APIs
    colors = ['#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0', '#9966FF', '#FF9F40']
    
    # Get common time labels from first API
    first_api = apis[0]
    first_logs = APILog.query.filter(
        APILog.api_id == first_api.id,
        APILog.timestamp >= cutoff
    ).order_by(APILog.timestamp.asc()).all()
    
    if not first_logs:
        return jsonify({
            'labels': [],
            'datasets': [],
            'chart_type': chart_type
        })
    
    labels = [log.timestamp.strftime('%H:%M') for log in first_logs]
    
    # Build datasets for each API
    datasets = []
    for idx, api in enumerate(apis):
        logs = APILog.query.filter(
            APILog.api_id == api.id,
            APILog.timestamp >= cutoff
        ).order_by(APILog.timestamp.asc()).all()
        
        if chart_type == 'pie' or chart_type == 'doughnut':
            success = len([l for l in logs if l.status_code == 200])
            failed = len(logs) - success
            datasets.append({
                'label': api.name,
                'data': [success, failed],
                'backgroundColor': [colors[idx % len(colors)], '#cccccc']
            })
        else:  # line, bar, area
            response_times = [log.response_time if log.response_time else 0 for log in logs]
            datasets.append({
                'label': api.name,
                'data': response_times,
                'borderColor': colors[idx % len(colors)],
                'backgroundColor': colors[idx % len(colors)] + '33',
                'borderWidth': 2,
                'tension': 0.4,
                'fill': chart_type == 'area'
            })
    
    return jsonify({
        'labels': labels,
        'datasets': datasets,
        'chart_type': chart_type
    })

@main_bp.route('/api/analytics/all')
@login_required
def get_all_analytics():
    """Get analytics for all user's APIs"""
    hours = request.args.get('hours', 24, type=int)
    cutoff = datetime.utcnow() - timedelta(hours=hours)
    
    # Get all APIs for current user
    apis = API.query.filter_by(user_id=current_user.id).all()
    
    total_requests = 0
    success_count = 0
    api_stats = []
    
    for api in apis:
        logs = APILog.query.filter(
            APILog.api_id == api.id,
            APILog.timestamp >= cutoff
        ).all()
        
        if logs:
            api_success = len([l for l in logs if l.status_code == 200])
            avg_time = sum(l.response_time for l in logs if l.response_time) / len([l for l in logs if l.response_time]) if any(l.response_time for l in logs) else 0
            
            total_requests += len(logs)
            success_count += api_success
            
            api_stats.append({
                'name': api.name,
                'requests': len(logs),
                'success': api_success,
                'uptime': round((api_success / len(logs) * 100), 2),
                'avg_response_time': round(avg_time, 2)
            })
    
    return jsonify({
        'total_requests': total_requests,
        'success_count': success_count,
        'failure_count': total_requests - success_count,
        'uptime': round((success_count / total_requests * 100), 2) if total_requests else 0,
        'apis': api_stats
    })

@main_bp.route('/api/chart-data/<int:api_id>')
@login_required
def get_chart_data(api_id):
    """Get chart data for graphs with support for multiple chart types"""
    api = API.query.get_or_404(api_id)
    if api.user_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403
    
    hours = request.args.get('hours', 24, type=int)
    chart_type = request.args.get('type', 'line')  # line, bar, pie, area
    cutoff = datetime.utcnow() - timedelta(hours=hours)
    
    logs = APILog.query.filter(
        APILog.api_id == api_id,
        APILog.timestamp >= cutoff
    ).order_by(APILog.timestamp.asc()).all()
    
    if not logs:
        return jsonify({
            'labels': [],
            'response_times': [],
            'status_codes': [],
            'timestamps': [],
            'chart_type': chart_type
        })
    
    # Prepare data based on chart type
    if chart_type == 'pie' or chart_type == 'doughnut':
        # For pie/doughnut: aggregate by status
        success = len([l for l in logs if l.status_code == 200])
        failed = len(logs) - success
        return jsonify({
            'labels': ['Success', 'Failed'],
            'data': [success, failed],
            'chart_type': chart_type
        })
    
    elif chart_type == 'bar':
        # Aggregate by hour for bar chart
        hourly_data = {}
        for log in logs:
            hour_key = log.timestamp.strftime('%H:00')
            if hour_key not in hourly_data:
                hourly_data[hour_key] = []
            if log.response_time:
                hourly_data[hour_key].append(log.response_time)
        
        return jsonify({
            'labels': list(hourly_data.keys()),
            'response_times': [sum(v)/len(v) if v else 0 for v in hourly_data.values()],
            'chart_type': chart_type
        })
    
    else:  # line or area (default)
        return jsonify({
            'labels': [log.timestamp.strftime('%H:%M') for log in logs],
            'response_times': [log.response_time if log.response_time else 0 for log in logs],
            'status_codes': [log.status_code for log in logs],
            'timestamps': [log.timestamp.isoformat() for log in logs],
            'chart_type': chart_type
        })

@main_bp.route('/api/analytics/<int:api_id>')
@login_required
def get_analytics(api_id):
    """Get analytics for an API"""
    api = API.query.get_or_404(api_id)
    if api.user_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403
    
    hours = request.args.get('hours', 24, type=int)
    cutoff = datetime.utcnow() - timedelta(hours=hours)
    
    logs = APILog.query.filter(
        APILog.api_id == api_id,
        APILog.timestamp >= cutoff
    ).all()
    
    if not logs:
        return jsonify({
            'total_requests': 0,
            'success_count': 0,
            'failure_count': 0,
            'avg_response_time': 0,
            'uptime': 0,
            'success_rate': 0
        })
    
    success_count = len([l for l in logs if l.status_code == 200])
    avg_response = sum(l.response_time for l in logs if l.response_time) / len([l for l in logs if l.response_time]) if any(l.response_time for l in logs) else 0
    
    return jsonify({
        'total_requests': len(logs),
        'success_count': success_count,
        'failure_count': len(logs) - success_count,
        'avg_response_time': round(avg_response, 2),
        'uptime': round((success_count / len(logs) * 100), 2) if logs else 0,
        'success_rate': round((success_count / len(logs) * 100), 2) if logs else 0
    })

@main_bp.route('/api/github-status')
@login_required
def get_github_status():
    """Get GitHub integration status"""
    try:
        # Try to get git remote info
        import subprocess
        result = subprocess.run(
            ['git', 'remote', '-v'],
            capture_output=True,
            text=True,
            cwd=str(PROJECT_ROOT)
        )
        has_remote = 'github.com' in result.stdout
        remote_url = ''
        if has_remote:
            lines = result.stdout.strip().split('\n')
            for line in lines:
                if 'origin' in line and '(fetch)' in line:
                    remote_url = line.split()[1]
                    break
        
        # Get last commit info
        commit_result = subprocess.run(
            ['git', 'log', '--oneline', '-1'],
            capture_output=True,
            text=True,
            cwd=str(PROJECT_ROOT)
        )
        last_commit = commit_result.stdout.strip() if commit_result.returncode == 0 else 'N/A'
        
        # Get current branch
        branch_result = subprocess.run(
            ['git', 'rev-parse', '--abbrev-ref', 'HEAD'],
            capture_output=True,
            text=True,
            cwd=str(PROJECT_ROOT)
        )
        current_branch = branch_result.stdout.strip() if branch_result.returncode == 0 else 'unknown'
        
        return jsonify({
            'connected': has_remote,
            'remote_url': remote_url,
            'last_commit': last_commit,
            'current_branch': current_branch,
            'status': 'Connected' if has_remote else 'Not connected'
        })
    except Exception as e:
        return jsonify({
            'connected': False,
            'status': f'Error: {str(e)}',
            'remote_url': '',
            'last_commit': 'N/A',
            'current_branch': 'N/A'
        }), 500

@main_bp.route('/api/deployment-status')
@login_required
def get_deployment_status():
    """Get deployment status info"""
    try:
        import subprocess
        import os
        
        # Check Docker status
        docker_check = subprocess.run(
            ['docker', '--version'],
            capture_output=True,
            text=True
        )
        docker_available = docker_check.returncode == 0
        docker_version = docker_check.stdout.strip() if docker_available else 'Not installed'
        
        # Check for Docker image
        image_check = subprocess.run(
            ['docker', 'images', '--format', '{{.Repository}}:{{.Tag}}'],
            capture_output=True,
            text=True
        )
        has_image = 'api-monitor' in image_check.stdout if image_check.returncode == 0 else False
        
        # Check if database exists
        db_path = PROJECT_ROOT / 'instance' / 'database.db'
        db_exists = db_path.exists()
        
        # Check for workflow files
        workflow_path = PROJECT_ROOT / '.github' / 'workflows' / 'python-app.yml'
        has_workflow = workflow_path.exists()
        grafana_path = PROJECT_ROOT / 'monitoring' / 'grafana'
        prometheus_path = PROJECT_ROOT / 'monitoring' / 'prometheus' / 'prometheus.yml'
        has_grafana = grafana_path.exists()
        has_prometheus = prometheus_path.exists()
        
        return jsonify({
            'docker': {
                'available': docker_available,
                'version': docker_version,
                'image_exists': has_image,
                'status': 'Available' if docker_available else 'Not installed'
            },
            'database': {
                'exists': db_exists,
                'path': str(db_path) if db_exists else 'Not found',
                'status': 'Ready' if db_exists else 'Not initialized'
            },
            'ci_cd': {
                'workflow_exists': has_workflow,
                'workflow_path': str(workflow_path) if has_workflow else 'Not found',
                'status': 'Configured' if has_workflow else 'Not configured'
            },
            'observability': {
                'grafana_exists': has_grafana,
                'prometheus_exists': has_prometheus,
                'grafana_path': str(grafana_path) if has_grafana else 'Not found',
                'prometheus_path': str(prometheus_path) if has_prometheus else 'Not found',
                'status': 'Configured' if has_grafana and has_prometheus else 'Not configured'
            }
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ==================== ALERT MANAGEMENT ====================

def generate_alerts_for_api(api):
    """Generate alerts based on the latest API log"""
    last_log = api.get_last_log()
    
    if not last_log:
        return
    
    # Check for OFFLINE alert (Connection refused, DNS failure)
    if last_log.error_message and ('Connection' in last_log.error_message or 'DNS' in last_log.error_message or 'refused' in last_log.error_message or 'Name or service not known' in last_log.error_message or 'does not exist' in str(last_log.error_message).lower()):
        # Resolve any open performance/error alerts for this API
        Alert.query.filter(Alert.api_id == api.id, Alert.is_active == True, Alert.alert_type.in_(['error', 'slow'])).update({'is_active': False, 'resolved_at': datetime.utcnow()}, synchronize_session=False)
        
        # Check if offline alert already exists
        existing_alert = Alert.query.filter_by(api_id=api.id, is_active=True, alert_type='offline').first()
        if not existing_alert:
            alert = Alert(
                api_id=api.id,
                alert_type='offline',
                severity='critical',
                message=f'API "{api.name}" is OFFLINE - Connection failed'
            )
            db.session.add(alert)
            db.session.commit()
    
    # Check for ERROR alert (Status code != 200)
    elif last_log.status_code and last_log.status_code != 200:
        # Resolve offline alert if exists
        Alert.query.filter_by(api_id=api.id, is_active=True, alert_type='offline').update({'is_active': False, 'resolved_at': datetime.utcnow()}, synchronize_session=False)
        
        # Check if error alert already exists for this status code
        existing_alert = Alert.query.filter_by(api_id=api.id, is_active=True, alert_type='error', status_code=last_log.status_code).first()
        if not existing_alert:
            alert = Alert(
                api_id=api.id,
                alert_type='error',
                severity='error',
                message=f'API "{api.name}" returned error status: {last_log.status_code}',
                status_code=last_log.status_code
            )
            db.session.add(alert)
            db.session.commit()
    
    # Check for SLOW alert (Response time exceeds threshold)
    elif last_log.response_time and last_log.response_time > api.threshold_latency:
        # Resolve offline and error alerts
        Alert.query.filter(Alert.api_id == api.id, Alert.is_active == True, Alert.alert_type.in_(['offline', 'error'])).update({'is_active': False, 'resolved_at': datetime.utcnow()}, synchronize_session=False)
        
        # Check if slow alert already exists
        existing_alert = Alert.query.filter_by(api_id=api.id, is_active=True, alert_type='slow').first()
        if not existing_alert:
            alert = Alert(
                api_id=api.id,
                alert_type='slow',
                severity='warning',
                message=f'API "{api.name}" is SLOW - Response time: {last_log.response_time}ms (threshold: {api.threshold_latency}ms)',
                response_time=last_log.response_time
            )
            db.session.add(alert)
            db.session.commit()
    
    # If successful (200), resolve all alerts
    elif last_log.status_code == 200:
        Alert.query.filter_by(api_id=api.id, is_active=True).update({'is_active': False, 'resolved_at': datetime.utcnow()}, synchronize_session=False)
        db.session.commit()


@main_bp.route('/api/alerts')
@login_required
def get_alerts():
    """Get all active alerts for the current user"""
    # First, generate alerts for all user's APIs
    apis = API.query.filter_by(user_id=current_user.id).all()
    for api in apis:
        generate_alerts_for_api(api)
    
    # Get all active alerts
    active_alerts = Alert.query.join(API).filter(
        API.user_id == current_user.id,
        Alert.is_active == True
    ).all()
    
    return jsonify({
        'alerts': [alert.to_dict() for alert in active_alerts],
        'count': len(active_alerts)
    })


@main_bp.route('/api/alerts/count')
@login_required
def get_alert_count():
    """Return active alert count for navbar badge updates."""
    return jsonify({
        'count': count_active_alerts(current_user.id)
    })


@main_bp.route('/api/alerts/<int:alert_id>/resolve', methods=['POST'])
@login_required
def resolve_alert(alert_id):
    """Resolve/close an alert"""
    alert = Alert.query.get_or_404(alert_id)
    
    # Check authorization
    api = alert.api
    if api.user_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403
    
    alert.is_active = False
    alert.resolved_at = datetime.utcnow()
    db.session.commit()
    
    return jsonify({'success': True, 'message': 'Alert resolved'})


# ==================== PDF EXPORT ====================

def generate_pdf_report(api_id=None):
    """Generate PDF report for API monitoring data"""
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    elements = []
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#1f77b4'),
        spaceAfter=30,
        alignment=0  # Left align
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=14,
        textColor=colors.HexColor('#1f77b4'),
        spaceAfter=12,
        spaceBefore=12
    )
    
    if api_id:
        # Single API report
        api = API.query.get_or_404(api_id)
        if api.user_id != current_user.id:
            return None
        
        # Title
        elements.append(Paragraph(f"API Monitoring Report: {api.name}", title_style))
        elements.append(Paragraph(f"Generated on: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC", styles['Normal']))
        elements.append(Spacer(1, 0.3*inch))
        
        # API Details
        elements.append(Paragraph("API Details", heading_style))
        api_data = [
            ['Property', 'Value'],
            ['URL', api.url],
            ['Interval', f'{api.interval} seconds'],
            ['Threshold Latency', f'{api.threshold_latency} ms'],
            ['Status', 'Active' if api.is_active else 'Inactive'],
            ['Created', api.created_at.strftime('%Y-%m-%d %H:%M:%S')]
        ]
        api_table = Table(api_data, colWidths=[2*inch, 4*inch])
        api_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1f77b4')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey])
        ]))
        elements.append(api_table)
        elements.append(Spacer(1, 0.3*inch))
        
        # Analytics for last 24 hours
        elements.append(Paragraph("24-Hour Analytics", heading_style))
        analytics = api.get_uptime_percentage(), api.get_avg_response_time()
        
        cutoff = datetime.utcnow() - timedelta(hours=24)
        logs = APILog.query.filter(APILog.api_id == api_id, APILog.timestamp >= cutoff).all()
        success_count = len([l for l in logs if l.status_code == 200])
        
        analytics_data = [
            ['Metric', 'Value'],
            ['Total Requests', str(len(logs))],
            ['Successful Requests', str(success_count)],
            ['Failed Requests', str(len(logs) - success_count)],
            ['Uptime %', f"{analytics[0]:.2f}%"],
            ['Avg Response Time', f"{analytics[1]:.2f} ms"]
        ]
        
        analytics_table = Table(analytics_data, colWidths=[2.5*inch, 3.5*inch])
        analytics_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1f77b4')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey])
        ]))
        elements.append(analytics_table)
        elements.append(Spacer(1, 0.3*inch))
        
        # Failure Risk Assessment
        risk_assessment = api.predict_failure_risk()
        elements.append(Paragraph("Failure Risk Assessment", heading_style))
        risk_data = [
            ['Property', 'Value'],
            ['Risk Level', risk_assessment['risk_level'].upper()],
            ['Risk Score', str(risk_assessment['risk_score'])],
            ['Confidence', f"{risk_assessment['confidence']:.1f}%"],
            ['Failure Rate', f"{risk_assessment['failure_rate']:.1f}%"]
        ]
        
        risk_table = Table(risk_data, colWidths=[2.5*inch, 3.5*inch])
        risk_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#d62728')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.pink),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey])
        ]))
        elements.append(risk_table)
        
    else:
        # All APIs report
        apis = API.query.filter_by(user_id=current_user.id).all()
        
        elements.append(Paragraph("API Monitoring Summary Report", title_style))
        elements.append(Paragraph(f"Generated on: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC", styles['Normal']))
        elements.append(Spacer(1, 0.3*inch))
        
        elements.append(Paragraph("All APIs Summary", heading_style))
        
        all_data = [['API Name', 'URL', 'Status', 'Uptime %', 'Avg Response (ms)']]
        
        for api in apis:
            status = 'Active' if api.is_active else 'Inactive'
            uptime = api.get_uptime_percentage()
            avg_response = api.get_avg_response_time()
            all_data.append([
                api.name[:20],
                api.url[:25],
                status,
                f"{uptime:.1f}%",
                f"{avg_response:.0f}"
            ])
        
        all_table = Table(all_data, colWidths=[1.2*inch, 1.8*inch, 0.8*inch, 1*inch, 1.2*inch])
        all_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1f77b4')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey])
        ]))
        elements.append(all_table)
    
    doc.build(elements)
    buffer.seek(0)
    return buffer


@main_bp.route('/api/export-pdf/<int:api_id>')
@login_required
def export_pdf_api(api_id):
    """Export single API report as PDF"""
    pdf_buffer = generate_pdf_report(api_id=api_id)
    if not pdf_buffer:
        return jsonify({'error': 'Unauthorized'}), 403
    
    api = API.query.get_or_404(api_id)
    filename = f"api_report_{api.name}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.pdf"
    
    return send_file(
        pdf_buffer,
        mimetype='application/pdf',
        as_attachment=True,
        download_name=filename
    )


@main_bp.route('/api/export-pdf')
@login_required
def export_pdf_all():
    """Export all APIs report as PDF"""
    pdf_buffer = generate_pdf_report()
    filename = f"monitoring_report_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.pdf"
    
    return send_file(
        pdf_buffer,
        mimetype='application/pdf',
        as_attachment=True,
        download_name=filename
    )


# ==================== LOGS PAGE ====================

@main_bp.route('/logs')
@login_required
def logs_page():
    """Display API logs page with filtering and search"""
    page = request.args.get('page', 1, type=int)
    api_id = request.args.get('api_id', None, type=int)
    search = request.args.get('search', '', type=str)
    hours = request.args.get('hours', 24, type=int)
    status_filter = request.args.get('status', '', type=str)
    
    # Get user's APIs
    apis = API.query.filter_by(user_id=current_user.id).all()
    
    # Build query
    query = APILog.query.join(API).filter(API.user_id == current_user.id)
    
    # Filter by API ID if provided
    if api_id:
        api = API.query.get_or_404(api_id)
        if api.user_id != current_user.id:
            flash('Unauthorized', 'error')
            return redirect(url_for('main.dashboard'))
        query = query.filter(APILog.api_id == api_id)
    
    # Filter by hours
    cutoff = datetime.utcnow() - timedelta(hours=hours)
    query = query.filter(APILog.timestamp >= cutoff)
    
    # Filter by status
    if status_filter:
        if status_filter == 'success':
            query = query.filter(APILog.is_success == True)
        elif status_filter == 'error':
            query = query.filter(APILog.is_success == False)
    
    # Filter by search term (in error message or URL)
    if search:
        query = query.filter(
            (APILog.error_message.ilike(f'%{search}%')) |
            (API.url.ilike(f'%{search}%'))
        )
    
    # Paginate
    pagination = query.order_by(APILog.timestamp.desc()).paginate(
        page=page, per_page=50
    )
    logs = pagination.items
    
    return render_template('logs.html',
        logs=logs,
        apis=apis,
        selected_api=api_id,
        search=search,
        hours=hours,
        status_filter=status_filter,
        pagination=pagination
    )


@main_bp.route('/api/logs')
@login_required
def get_logs_api():
    """Get logs as JSON API endpoint"""
    page = request.args.get('page', 1, type=int)
    api_id = request.args.get('api_id', None, type=int)
    hours = request.args.get('hours', 24, type=int)
    
    query = APILog.query.join(API).filter(API.user_id == current_user.id)
    
    if api_id:
        api = API.query.get_or_404(api_id)
        if api.user_id != current_user.id:
            return jsonify({'error': 'Unauthorized'}), 403
        query = query.filter(APILog.api_id == api_id)
    
    cutoff = datetime.utcnow() - timedelta(hours=hours)
    query = query.filter(APILog.timestamp >= cutoff)
    
    pagination = query.order_by(APILog.timestamp.desc()).paginate(
        page=page, per_page=50
    )
    
    logs_data = [{
        'id': log.id,
        'api_name': log.api.name,
        'api_id': log.api_id,
        'status_code': log.status_code,
        'response_time': log.response_time,
        'is_success': log.is_success,
        'error_message': log.error_message,
        'timestamp': log.timestamp.isoformat()
    } for log in pagination.items]
    
    return jsonify({
        'logs': logs_data,
        'total': pagination.total,
        'pages': pagination.pages,
        'current_page': page
    })


# ==================== LOGS EXPORT ====================

@main_bp.route('/logs/export-csv')
@login_required
def export_logs_csv():
    """Export logs as CSV with filters applied"""
    api_id = request.args.get('api_id', None, type=int)
    search = request.args.get('search', '', type=str)
    hours = request.args.get('hours', 24, type=int)
    status_filter = request.args.get('status', '', type=str)
    
    # Build query with filters
    query = APILog.query.join(API).filter(API.user_id == current_user.id)
    
    if api_id:
        api = API.query.get_or_404(api_id)
        if api.user_id != current_user.id:
            return abort(403)
        query = query.filter(APILog.api_id == api_id)
    
    cutoff = datetime.utcnow() - timedelta(hours=hours)
    query = query.filter(APILog.timestamp >= cutoff)
    
    if status_filter == 'success':
        query = query.filter(APILog.is_success == True)
    elif status_filter == 'error':
        query = query.filter(APILog.is_success == False)
    
    if search:
        query = query.filter(
            (APILog.error_message.ilike(f'%{search}%')) |
            (API.url.ilike(f'%{search}%'))
        )
    
    logs = query.order_by(APILog.timestamp.desc()).all()
    
    # Create CSV
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(['Timestamp', 'API', 'URL', 'Status Code', 'Response Time (ms)', 'Status', 'Error Message'])
    
    for log in logs:
        writer.writerow([
            log.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            log.api.name,
            log.api.url,
            log.status_code,
            log.response_time if log.response_time else 'N/A',
            'Success' if log.is_success else 'Error',
            log.error_message or ''
        ])
    
    filename = f"logs_export_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"
    
    return send_file(
        BytesIO(output.getvalue().encode('utf-8')),
        mimetype='text/csv',
        as_attachment=True,
        download_name=filename
    )


@main_bp.route('/logs/export-pdf')
@login_required
def export_logs_pdf():
    """Export logs as PDF with filters applied"""
    api_id = request.args.get('api_id', None, type=int)
    search = request.args.get('search', '', type=str)
    hours = request.args.get('hours', 24, type=int)
    status_filter = request.args.get('status', '', type=str)
    
    # Build query with filters
    query = APILog.query.join(API).filter(API.user_id == current_user.id)
    
    if api_id:
        api = API.query.get_or_404(api_id)
        if api.user_id != current_user.id:
            return abort(403)
        query = query.filter(APILog.api_id == api_id)
    
    cutoff = datetime.utcnow() - timedelta(hours=hours)
    query = query.filter(APILog.timestamp >= cutoff)
    
    if status_filter == 'success':
        query = query.filter(APILog.is_success == True)
    elif status_filter == 'error':
        query = query.filter(APILog.is_success == False)
    
    if search:
        query = query.filter(
            (APILog.error_message.ilike(f'%{search}%')) |
            (API.url.ilike(f'%{search}%'))
        )
    
    logs = query.order_by(APILog.timestamp.desc()).all()
    
    # Create PDF
    pdf_buffer = BytesIO()
    doc = SimpleDocTemplate(pdf_buffer, pagesize=letter)
    elements = []
    
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#1f77b4'),
        spaceAfter=30,
        alignment=1
    )
    
    title = Paragraph(f"API Logs Export - {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}", title_style)
    elements.append(title)
    elements.append(Spacer(1, 0.2*inch))
    
    # Prepare table data
    table_data = [['Timestamp', 'API', 'Status Code', 'Response Time', 'Status', 'Error']]
    
    for log in logs[:100]:  # Limit to first 100 for performance
        table_data.append([
            log.timestamp.strftime('%Y-%m-%d %H:%M'),
            log.api.name[:20],
            str(log.status_code),
            f"{log.response_time}ms" if log.response_time else 'N/A',
            'Success' if log.is_success else 'Error',
            (log.error_message[:30] if log.error_message else '')
        ])
    
    # Create table with styling
    table = Table(table_data, colWidths=[1.2*inch, 1.2*inch, 1*inch, 1*inch, 0.8*inch, 1.5*inch])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1f77b4')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 11),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
    ]))
    
    elements.append(table)
    
    doc.build(elements)
    pdf_buffer.seek(0)
    
    filename = f"logs_export_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.pdf"
    
    return send_file(
        pdf_buffer,
        mimetype='application/pdf',
        as_attachment=True,
        download_name=filename
    )
