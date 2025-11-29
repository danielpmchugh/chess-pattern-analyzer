# Deployment Checklist

Use this checklist before deploying to production.

## Pre-Deployment

### Code Quality
- [ ] All tests passing (`pytest`)
- [ ] Code coverage > 80% (`pytest --cov`)
- [ ] No linting errors (`ruff check app/`)
- [ ] Code formatted (`black app/`)
- [ ] Type hints checked (`mypy app/`)
- [ ] Dependencies updated and pinned in requirements.txt
- [ ] No TODO/FIXME comments in critical paths
- [ ] Secrets removed from code (use environment variables)

### Configuration
- [ ] `.env.example` is up to date
- [ ] No `.env` file committed to Git
- [ ] All required environment variables documented
- [ ] `DEBUG=false` for production
- [ ] `ENVIRONMENT=production` set
- [ ] `LOG_LEVEL=INFO` or `WARNING` for production
- [ ] `ENABLE_DETAILED_ERRORS=false` for production
- [ ] Strong `SECRET_KEY` generated (32+ characters)

### External Services
- [ ] Neon PostgreSQL database created
- [ ] Neon connection string obtained
- [ ] Upstash Redis database created
- [ ] Upstash connection string obtained
- [ ] Stockfish binary tested locally
- [ ] Chess.com API accessible (no firewall blocks)

## Deployment to Railway

### Railway Setup
- [ ] Railway account created
- [ ] GitHub repository connected
- [ ] Railway project created
- [ ] Service configured

### Environment Variables
- [ ] `DATABASE_URL` set (from Neon)
- [ ] `REDIS_URL` set (from Upstash)
- [ ] `SECRET_KEY` generated and set
- [ ] `ENVIRONMENT=production` set
- [ ] `DEBUG=false` set
- [ ] `LOG_LEVEL=INFO` set
- [ ] `CORS_ORIGINS` set (with frontend URL)
- [ ] `ENABLE_DETAILED_ERRORS=false` set
- [ ] Optional: `SENTRY_DSN` set (if using Sentry)

### Build & Deploy
- [ ] Dockerfile builds successfully locally
- [ ] Docker image tested locally
- [ ] Railway deployment triggered
- [ ] Build logs checked (no errors)
- [ ] Deployment successful
- [ ] Railway URL obtained

## Post-Deployment Verification

### Health Checks
- [ ] `/healthz` returns 200 OK
- [ ] `/api/v1/health` returns healthy status
- [ ] `/api/v1/health/live` returns alive
- [ ] `/api/v1/health/ready` shows all services ready
- [ ] Redis check passes
- [ ] Stockfish check passes
- [ ] Database check passes

### API Functionality
- [ ] Root endpoint `/` accessible
- [ ] API documentation `/api/docs` loads
- [ ] OpenAPI schema `/api/openapi.json` valid
- [ ] CORS headers present in responses
- [ ] Request IDs in response headers

### Performance
- [ ] Health check responds < 500ms
- [ ] Cold start time < 5 seconds
- [ ] API responses < 2 seconds
- [ ] No memory leaks observed
- [ ] CPU usage reasonable

### Monitoring
- [ ] Logs visible in Railway dashboard
- [ ] Error tracking working (if Sentry configured)
- [ ] Health check monitoring enabled
- [ ] Uptime monitoring configured (optional)

### Security
- [ ] HTTPS enabled (Railway provides automatically)
- [ ] CORS properly configured (no wildcard in production)
- [ ] Error messages don't expose internal details
- [ ] Database credentials not in logs
- [ ] API rate limiting ready (to be implemented)

## Domain & DNS (Optional)

If using custom domain:
- [ ] Domain purchased
- [ ] DNS records configured
- [ ] CNAME pointing to Railway
- [ ] SSL certificate issued
- [ ] Custom domain accessible
- [ ] `CORS_ORIGINS` updated with custom domain

## Documentation

- [ ] README.md updated
- [ ] DEPLOYMENT.md reviewed
- [ ] API documentation generated
- [ ] Environment variables documented
- [ ] Deployment URL shared with team

## Rollback Plan

- [ ] Previous deployment accessible in Railway
- [ ] Database backups available (Neon automatic backups)
- [ ] Rollback procedure documented
- [ ] Emergency contact list ready

## Monitoring Setup

### Recommended (Optional)
- [ ] Sentry error tracking
- [ ] Better Uptime monitoring
- [ ] Railway alerts configured
- [ ] Slack/Discord webhooks for alerts

## Cost Management

- [ ] Railway usage monitored
- [ ] Neon storage checked (< 0.5GB)
- [ ] Upstash commands tracked (< 10k/day)
- [ ] Alerts set for approaching limits
- [ ] Budget alarms configured

## First Week Checklist

After deployment, monitor for one week:
- [ ] Day 1: Check logs every few hours
- [ ] Day 2: Verify no errors in Sentry
- [ ] Day 3: Check database size
- [ ] Day 4: Verify Redis command usage
- [ ] Day 5: Check Railway resource usage
- [ ] Day 6: Review error rates
- [ ] Day 7: Performance audit

## Issue Response

If issues occur:
1. Check Railway logs
2. Verify all environment variables
3. Check Neon database status (may auto-pause)
4. Verify Upstash Redis connectivity
5. Review recent deployments
6. Check for rate limiting hits
7. Consider rollback if critical

## Sign-Off

- [ ] Technical lead approval
- [ ] Deployment verified by backend developer
- [ ] Frontend team notified of API URL
- [ ] Documentation team updated

## Notes

Deployment Date: _______________
Deployed By: _______________
Railway URL: _______________
Frontend URL: _______________
Issues Encountered: _______________
