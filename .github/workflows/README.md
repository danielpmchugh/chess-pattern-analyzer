# GitHub Actions CI/CD Workflows

This directory contains automated workflows for the Chess Pattern Analyzer project.

## Workflows

### `backend-ci.yml` - Backend Continuous Integration

**Triggers:**
- Push to `main` branch (when backend files change)
- Pull requests to `main` branch (when backend files change)

**What it does:**
1. ✅ **Docker Build Test** - Builds the Docker image to catch dependency conflicts
2. ✅ **Dependency Check** - Verifies no duplicate packages in requirements.txt
3. ✅ **Python Setup** - Installs dependencies to verify they're compatible
4. ✅ **Linting** - Runs ruff to check code quality (non-blocking)
5. ✅ **Tests** - Runs unit tests for core components
6. ✅ **Dockerfile Validation** - Checks Dockerfile for best practices

**Benefits:**
- Catches dependency conflicts before they reach Render
- Validates Docker build works
- Ensures code quality
- Runs tests automatically
- Fails fast if there are issues

## Status Badges

Add this to your main README to show build status:

```markdown
![Backend CI](https://github.com/danielpmchugh/chess-pattern-analyzer/workflows/Backend%20CI/badge.svg)
```

## Local Testing

To test what CI will check:

```bash
# Build Docker image
cd backend
docker build -t chess-api:test .

# Run tests
pytest app/tests/test_config.py app/tests/test_exceptions.py -v

# Check for duplicates
grep -v '^#' requirements.txt | grep -v '^$' | cut -d'>' -f1 | cut -d'=' -f1 | cut -d'<' -f1 | sort | uniq -d
```

## Future Enhancements

- [ ] Add frontend CI workflow
- [ ] Add security scanning (Snyk, Trivy)
- [ ] Add code coverage reporting
- [ ] Add automatic dependency updates (Dependabot)
- [ ] Add deployment to staging environment
