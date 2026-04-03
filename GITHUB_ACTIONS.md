# GitHub Actions Workflow Configuration

## Overview

This project uses GitHub Actions for continuous integration and deployment (CI/CD). The workflows are designed to automatically test, build, and deploy the application when code is pushed to the repository.

## Workflow Files

### 1. **python-app.yml** - Python Tests & Build
**Purpose:** Test Python code and build Docker images

**Jobs:**
- `code-quality`: Runs flake8 linting checks
- `test`: Runs unit tests on Python 3.10, 3.11, and 3.12
- `build`: Builds Docker image and validates it

**Triggers:** Push or pull request to main/master branches

### 2. **ci-cd.yml** - CI/CD Pipeline
**Purpose:** Core CI/CD pipeline with comprehensive checks

**Jobs:**
- `test`: Runs tests with coverage reporting
- `security-scan`: Runs Bandit security scanning
- `build-docker`: Builds and tests Docker image
- `deploy`: Deployment placeholder (configure for your infrastructure)
- `notify`: Success notification

**Triggers:** Push or pull request to main/master branches

### 3. **integration-tests.yml** - Integration Tests
**Purpose:** Run integration tests and API validation

**Jobs:**
- `integration-tests`: Runs Pytest integration suite
- `docker-build`: Builds and validates Docker image
- `security-scan`: Runs security analysis with Bandit and Safety

**Triggers:** Push or pull request to main/master branches

### 4. **deploy-prod.yml** - Deploy to Production
**Purpose:** Production deployment pipeline

**Jobs:**
- `test`: Verifies all tests pass
- `build`: Builds production Docker image
- `deploy`: Validates deployment configuration
- `notify`: Deployment completion notification

**Triggers:** Push to main/master with changes to app/, requirements.txt, Dockerfile, or workflows

## Fix Summary

### Issues Fixed

1. **Removed `|| true` statements** that were silently passing failed tests
   - Tests now properly fail when they encounter issues
   - GitHub Actions correctly reports test failures

2. **Added proper error handling**
   - Critical tests fail the workflow
   - Non-critical tests (like Selenium) use `continue-on-error: true`

3. **Created missing workflows**
   - `integration-tests.yml` for API testing
   - `deploy-prod.yml` for production deployment

4. **Added security scanning**
   - Bandit for code security vulnerabilities
   - Safety for dependency vulnerabilities

5. **Improved test configuration**
   - Created `pytest.ini` for consistent pytest setup
   - Proper test discovery and markers

6. **Added coverage reporting**
   - Code coverage tracking with pytest-cov
   - Better test visibility in CI/CD

## How to Use

### Local Testing Before Push

Run the verification script to test everything locally:

```bash
python verify_ci.py
```

This will check:
- Python syntax
- Requirements installation
- App initialization
- Unit tests
- Code linting
- Database models

### Manual Test Execution

```bash
# Run all unit tests
pytest tests/test_app.py -v

# Run with coverage
pytest tests/ -v --cov=app

# Run specific test
pytest tests/test_app.py::test_app_creation -v

# Run linting
flake8 app/ --count

# Security scan
bandit -r app/ -ll
```

### Docker Testing

```bash
# Build Docker image
docker build -t api-monitor:latest .

# Test Docker image
docker run --rm -e "START_MONITOR=false" api-monitor:latest python -c "from app import create_app; app = create_app(); print('✓ OK')"
```

## Troubleshooting

### Issue: Tests fail in GitHub Actions but pass locally

**Solution:**
1. Check Python version matches (3.10, 3.11, 3.12)
2. Verify all dependencies in `requirements.txt`
3. Ensure `conftest.py` has all required fixtures
4. Use `pytest.ini` for consistent configuration

### Issue: Docker build fails

**Solution:**
1. Check `Dockerfile` syntax
2. Verify `requirements.txt` is valid
3. Test build locally: `docker build -t api-monitor:latest .`
4. Check Python base image availability

### Issue: Tests hang or timeout

**Solution:**
1. Check for blocking operations in tests
2. Set proper timeouts in test fixtures
3. Use `-x` flag to stop at first failure: `pytest tests/ -x`
4. Check resource constraints (especially Selenium tests)

### Issue: Security scan reports vulnerabilities

**Solution:**
1. Review Bandit report for false positives
2. Update vulnerable dependencies
3. Use `# nosec` comment for intentional code patterns
4. Check `Safety` report for dependency vulnerabilities

## Best Practices

1. **Always run `verify_ci.py` before pushing**
```bash
python verify_ci.py
```

2. **Keep dependencies updated**
```bash
pip install --upgrade -r requirements.txt
```

3. **Fix linting issues immediately**
```bash
flake8 app/ --show-source --statistics
```

4. **Test with multiple Python versions locally**
```bash
# Use pyenv or similar to test with different Python versions
```

5. **Monitor workflow status**
- Check GitHub Actions tab for workflow runs
- Review failed job logs for debugging

## Configuration

### Customize for Your Infrastructure

The `deploy-prod.yml` file has a placeholder deployment job. Customize based on your infrastructure:

- **Kubernetes:** Use kubctl apply or Helm charts
- **Docker Compose:** Use docker-compose up
- **AWS:** Use CloudFormation or Terraform
- **GCP:** Use Google Cloud Deploy
- **Azure:** Use Azure DevOps

### Environment Variables

Configure these in GitHub repository settings → Secrets:

```
DATABASE_URL=<your-database-url>
SECRET_KEY=<your-secret-key>
DEPLOY_TOKEN=<deployment-token>
DOCKER_REGISTRY=<registry-url>
```

## Monitoring & Alerts

### GitHub Status Page

View all workflow statuses: Go to **Actions** tab in repository

### Enable Branch Protection

1. Go to **Settings** → **Branches**
2. Add rule for `main`/`master`
3. Require status checks to pass before merging
4. Select required workflows

### Email Notifications

Configure in **Settings** → **Notifications** to receive workflow failure alerts

## Resources

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Pytest Documentation](https://docs.pytest.org/)
- [Bandit Documentation](https://bandit.readthedocs.io/)
- [Docker Documentation](https://docs.docker.com/)
