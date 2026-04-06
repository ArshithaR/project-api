from app import db
from flask_login import UserMixin
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

class User(db.Model, UserMixin):
    """User model"""
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    apis = db.relationship('API', backref='user', lazy=True, cascade='all, delete-orphan')
    password_reset_codes = db.relationship('PasswordResetCode', back_populates='user', lazy=True, cascade='all, delete-orphan')
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class API(db.Model):
    """API Endpoint model"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    url = db.Column(db.String(500), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    interval = db.Column(db.Integer, default=60)  # seconds
    threshold_latency = db.Column(db.Integer, default=1000)  # ms
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    logs = db.relationship('APILog', backref='api', lazy=True, cascade='all, delete-orphan')
    alerts = db.relationship('Alert', back_populates='api', lazy=True, cascade='all, delete-orphan')
    
    def get_last_log(self):
        return APILog.query.filter_by(api_id=self.id).order_by(APILog.timestamp.desc()).first()
    
    def get_avg_response_time(self, hours=24):
        """Get average response time for last N hours"""
        from datetime import timedelta
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        logs = APILog.query.filter(
            APILog.api_id == self.id,
            APILog.timestamp >= cutoff
        ).all()
        if not logs:
            return 0
        # Filter out None values to avoid TypeError
        response_times = [l.response_time for l in logs if l.response_time is not None]
        if not response_times:
            return 0
        return sum(response_times) / len(response_times)
    
    def get_uptime_percentage(self, hours=24):
        """Calculate uptime % = (Successful Requests / Total Requests) * 100"""
        from datetime import timedelta
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        logs = APILog.query.filter(
            APILog.api_id == self.id,
            APILog.timestamp >= cutoff
        ).all()
        if not logs:
            return 100.0
        successful = sum(1 for log in logs if log.is_success)
        return (successful / len(logs)) * 100
    
    def get_response_time_trend(self, hours=24):
        """Get response time trend data for charts (hourly averages)"""
        from datetime import timedelta
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        logs = APILog.query.filter(
            APILog.api_id == self.id,
            APILog.timestamp >= cutoff,
            APILog.response_time != None
        ).all()
        
        # Group by hour
        hourly_data = {}
        for log in logs:
            hour_key = log.timestamp.strftime('%Y-%m-%d %H:00')
            if hour_key not in hourly_data:
                hourly_data[hour_key] = []
            hourly_data[hour_key].append(log.response_time)
        
        return [{'time': k, 'avg_response_time': sum(v) / len(v)} for k, v in sorted(hourly_data.items())]
    
    def get_success_failure_stats(self, hours=24):
        """Get success vs failure percentage"""
        from datetime import timedelta
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        logs = APILog.query.filter(
            APILog.api_id == self.id,
            APILog.timestamp >= cutoff
        ).all()
        
        if not logs:
            return {'success': 0, 'failure': 0}
        
        success = sum(1 for log in logs if log.is_success)
        failure = len(logs) - success
        total = len(logs)
        
        return {
            'success_count': success,
            'failure_count': failure,
            'success_pct': (success / total * 100) if total > 0 else 0,
            'failure_pct': (failure / total * 100) if total > 0 else 0
        }
    
    def get_peak_failure_hours(self, days=7):
        """Get failure distribution by hour (for heatmap)"""
        from datetime import timedelta
        cutoff = datetime.utcnow() - timedelta(days=days)
        logs = APILog.query.filter(
            APILog.api_id == self.id,
            APILog.timestamp >= cutoff
        ).all()
        
        # Create 24-hour grid
        failure_by_hour = {i: 0 for i in range(24)}
        total_by_hour = {i: 0 for i in range(24)}
        
        for log in logs:
            hour = log.timestamp.hour
            total_by_hour[hour] += 1
            if not log.is_success:
                failure_by_hour[hour] += 1
        
        return [
            {
                'hour': h,
                'failures': failure_by_hour.get(h, 0),
                'total': total_by_hour.get(h, 0),
                'failure_rate': (failure_by_hour.get(h, 0) / total_by_hour.get(h, 1) * 100) if total_by_hour.get(h, 0) > 0 else 0
            }
            for h in range(24)
        ]
    
    def predict_failure_risk(self):
        """Predict if API might fail based on recent trends - Basic ML logic"""
        from datetime import timedelta
        
        # Get last 24 hours of data
        cutoff = datetime.utcnow() - timedelta(hours=24)
        logs = APILog.query.filter(
            APILog.api_id == self.id,
            APILog.timestamp >= cutoff
        ).all()
        
        if len(logs) < 5:
            return {'risk_level': 'low', 'confidence': 0, 'reason': 'Not enough data'}
        
        recent_logs = logs[-10:]  # Last 10 requests
        failure_rate = sum(1 for log in recent_logs if not log.is_success) / len(recent_logs)
        
        # Get response times for trend
        response_times = [log.response_time for log in logs if log.response_time]
        if len(response_times) < 2:
            return {'risk_level': 'low', 'confidence': 0, 'reason': 'Insufficient response data'}
        
        avg_response = sum(response_times) / len(response_times)
        recent_avg = sum(log.response_time for log in recent_logs if log.response_time) / len([l for l in recent_logs if l.response_time])
        
        # Risk calculation
        risk_score = 0
        reasons = []
        
        # Factor 1: Recent failure rate
        if failure_rate > 0.5:
            risk_score += 40
            reasons.append(f"High failure rate ({failure_rate*100:.0f}%) in last 10 requests")
        elif failure_rate > 0.2:
            risk_score += 20
            reasons.append(f"Elevated failure rate ({failure_rate*100:.0f}%)")
        
        # Factor 2: Response time degradation
        if recent_avg > avg_response * 1.5:
            risk_score += 30
            reasons.append(f"Response time degrading (+{((recent_avg/avg_response - 1)*100):.0f}%)")
        
        # Factor 3: Consecutive failures
        recent_failures = sum(1 for log in recent_logs[-3:] if not log.is_success)
        if recent_failures >= 2:
            risk_score += 20
            reasons.append("Recent consecutive failures detected")
        
        # Determine risk level
        if risk_score >= 60:
            risk_level = 'high'
        elif risk_score >= 30:
            risk_level = 'medium'
        else:
            risk_level = 'low'
        
        return {
            'risk_level': risk_level,
            'risk_score': risk_score,
            'confidence': min(100, (len(logs) / 100) * 100),
            'failure_rate': failure_rate * 100,
            'reasons': reasons if reasons else ['System operating normally']
        }

class APILog(db.Model):
    """API monitoring log"""
    __tablename__ = 'api_log'
    id = db.Column(db.Integer, primary_key=True)
    api_id = db.Column(db.Integer, db.ForeignKey('api.id'), nullable=False)
    status_code = db.Column(db.Integer)
    response_time = db.Column(db.Float)  # milliseconds
    is_success = db.Column(db.Boolean, default=False)
    error_message = db.Column(db.String(500))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<APILog {self.api_id} - {self.status_code} - {self.response_time}ms>'


class Alert(db.Model):
    """Alert model for tracking API health alerts"""
    __tablename__ = 'alert'
    id = db.Column(db.Integer, primary_key=True)
    api_id = db.Column(db.Integer, db.ForeignKey('api.id', ondelete='CASCADE'), nullable=False)
    alert_type = db.Column(db.String(50), nullable=False)  # 'offline', 'error', 'slow'
    severity = db.Column(db.String(20), nullable=False)  # 'critical', 'error', 'warning'
    message = db.Column(db.String(500), nullable=False)
    status_code = db.Column(db.Integer, default=None)  # applicable for error alerts
    response_time = db.Column(db.Float, default=None)  # applicable for slow alerts
    is_active = db.Column(db.Boolean, default=True)  # whether alert is still ongoing
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    resolved_at = db.Column(db.DateTime, default=None)
    api = db.relationship('API', back_populates='alerts')
    
    def __repr__(self):
        return f'<Alert {self.api_id} - {self.alert_type} - {self.severity}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'api_id': self.api_id,
            'api_name': self.api.name,
            'alert_type': self.alert_type,
            'severity': self.severity,
            'message': self.message,
            'status_code': self.status_code,
            'response_time': self.response_time,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat(),
            'resolved_at': self.resolved_at.isoformat() if self.resolved_at else None,
        }


class PasswordResetCode(db.Model):
    """Password reset verification code."""
    __tablename__ = 'password_reset_code'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    code = db.Column(db.String(6), nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    used = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    user = db.relationship('User', back_populates='password_reset_codes')

    def is_valid(self):
        return not self.used and self.expires_at >= datetime.utcnow()
