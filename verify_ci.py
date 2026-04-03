#!/usr/bin/env python3
"""
Verification script to test the CI/CD setup locally.
Run this before pushing to GitHub to catch issues early.
"""

import subprocess
import sys
from pathlib import Path

def run_command(cmd, description):
    """Run a command and report results."""
    print(f"\n{'='*60}")
    print(f"Testing: {description}")
    print(f"{'='*60}")
    try:
        result = subprocess.run(
            cmd, 
            shell=True, 
            capture_output=True, 
            text=True,
            timeout=30
        )
        if result.returncode == 0:
            print(f"✅ PASSED: {description}")
            if result.stdout:
                print(result.stdout[:500])
            return True
        else:
            print(f"❌ FAILED: {description}")
            if result.stderr:
                print("Error:", result.stderr[:500])
            if result.stdout:
                print("Output:", result.stdout[:500])
            return False
    except subprocess.TimeoutExpired:
        print(f"⏱️  TIMEOUT: {description}")
        return False
    except Exception as e:
        print(f"❌ ERROR: {description} - {e}")
        return False

def main():
    """Run all verification tests."""
    print("\n" + "="*60)
    print("CI/CD VERIFICATION SCRIPT")
    print("="*60)
    
    base_dir = Path(__file__).parent
    results = {}
    
    # Test 1: Python syntax
    results["Python Syntax"] = run_command(
        "python -m py_compile app.py app/__init__.py app/models.py app/routes.py app/monitor.py",
        "Python syntax check"
    )
    
    # Test 2: Requirements
    results["Requirements Install"] = run_command(
        "pip install -r requirements.txt -q",
        "Install requirements"
    )
    
    # Test 3: App initialization
    results["App Init"] = run_command(
        'python -c "from app import create_app; app = create_app(\'\'\'{"TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:"}\'\'\')"',
        "App initialization"
    )
    
    # Test 4: Pytest
    results["Unit Tests"] = run_command(
        "pytest tests/test_app.py -v --tb=short",
        "Unit tests"
    )
    
    # Test 5: Flake8
    results["Flake8 Lint"] = run_command(
        "pip install flake8 -q && flake8 app/ --select=E9,F63,F7,F82 --count",
        "Flake8 linting"
    )
    
    # Test 6: Database models
    results["Database Models"] = run_command(
        'python -c "from app.models import User, API; print(\'✓ Models loaded\')"',
        "Database models"
    )
    
    # Print summary
    print("\n" + "="*60)
    print("VERIFICATION SUMMARY")
    print("="*60)
    
    total = len(results)
    passed = sum(1 for v in results.values() if v)
    failed = total - passed
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {test_name}")
    
    print(f"\nTotal: {passed}/{total} passed, {failed} failed")
    
    if failed == 0:
        print("\n🎉 All checks passed! Ready for GitHub Actions")
        return 0
    else:
        print(f"\n⚠️  {failed} check(s) failed. Fix before pushing to GitHub")
        return 1

if __name__ == "__main__":
    sys.exit(main())
