# Deployment Guide - Chess Pattern Analyzer API

This guide covers deploying the FastAPI backend to Railway with Neon PostgreSQL and Upstash Redis.

## Prerequisites

1. Railway account (https://railway.app)
2. Neon PostgreSQL account (https://neon.tech) - Free tier
3. Upstash Redis account (https://upstash.com) - Free tier
4. GitHub repository connected to Railway

## Step 1: Set Up Neon PostgreSQL

1. Go to https://neon.tech and sign up/log in
2. Create a new project:
   - Name: `chess-analyzer`
   - Region: Choose closest to your Railway deployment region
3. Get your connection string:
   - Go to your project dashboard
   - Click "Connection Details"
   - Copy the connection string (it looks like):
     ```
     postgresql://username:password@ep-xxx.us-east-2.aws.neon.tech/neondb?sslmode=require
     ```
4. Keep this connection string for Railway configuration

## Step 2: Set Up Upstash Redis

1. Go to https://upstash.com and sign up/log in
2. Create a new Redis database:
   - Name: `chess-analyzer-cache`
   - Region: Choose same as Railway deployment
   - Type: Regional (Free tier)
3. Get your connection string:
   - Click on your database
   - Copy the "Redis URL" (TLS enabled):
     ```
     rediss://default:xxxx@loving-fish-12345.upstash.io:6379
     ```
4. Keep this connection string for Railway configuration

## Step 3: Deploy to Railway

### Option A: Deploy from GitHub (Recommended)

1. Push your code to GitHub:
   ```bash
   cd /home/gspadz/github/chess
   git add backend/
   git commit -m "Add FastAPI backend implementation"
   git push origin main
   ```

2. Go to https://railway.app/new
3. Click "Deploy from GitHub repo"
4. Select your repository
5. Railway will detect the Dockerfile automatically

### Option B: Deploy with Railway CLI

1. Install Railway CLI:
   ```bash
   npm i -g @railway/cli
   ```

2. Login to Railway:
   ```bash
   railway login
   ```

3. Initialize project:
   ```bash
   cd backend
   railway init
   ```

4. Deploy:
   ```bash
   railway up
   ```

## Step 4: Configure Environment Variables in Railway

1. Go to your Railway project dashboard
2. Click on your service
3. Go to "Variables" tab
4. Add the following environment variables:

### Required Variables

```bash
# Application
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO

# Database (from Neon)
DATABASE_URL=postgresql://username:password@ep-xxx.us-east-2.aws.neon.tech/neondb?sslmode=require

# Redis (from Upstash)
REDIS_URL=rediss://default:xxxx@loving-fish-12345.upstash.io:6379

# Security (generate a secure random string)
SECRET_KEY=your-secure-secret-key-here

# CORS (your frontend domain - update after frontend deployment)
CORS_ORIGINS=["https://your-app.vercel.app"]
```

### Generate Secure Secret Key

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

### Optional Variables

```bash
# API Configuration
API_TIMEOUT=25

# Rate Limiting
RATE_LIMIT_ENABLED=true

# Caching
CACHE_ENABLED=true

# Feature Flags
ENABLE_SWAGGER_UI=true
ENABLE_METRICS=true
ENABLE_DETAILED_ERRORS=false

# Monitoring (optional - add if using Sentry)
SENTRY_DSN=your-sentry-dsn
SENTRY_ENVIRONMENT=production
```

## Step 5: Verify Deployment

1. Railway will automatically build and deploy
2. Check deployment logs in Railway dashboard
3. Once deployed, Railway will provide a URL like:
   ```
   https://chess-analyzer-production.up.railway.app
   ```

4. Test your deployment:
   ```bash
   # Health check
   curl https://your-railway-url.railway.app/healthz

   # API info
   curl https://your-railway-url.railway.app/

   # Detailed health
   curl https://your-railway-url.railway.app/api/v1/health/ready

   # API documentation
   open https://your-railway-url.railway.app/api/docs
   ```

## Step 6: Set Up Custom Domain (Optional)

1. In Railway dashboard, go to "Settings"
2. Scroll to "Domains"
3. Click "Generate Domain" for a Railway subdomain
4. Or add your custom domain:
   - Click "Custom Domain"
   - Enter your domain (e.g., api.yourdomain.com)
   - Update your DNS with the provided CNAME record

## Step 7: Monitor Your Application

### Health Checks

Railway automatically monitors your `/healthz` endpoint. You can also:

1. View logs in Railway dashboard
2. Set up log drains (optional)
3. Monitor metrics in Railway

### Recommended Monitoring

1. **Sentry** (Free tier - 5k events/month):
   - Sign up at https://sentry.io
   - Create a new project
   - Get your DSN
   - Add `SENTRY_DSN` to Railway environment variables

2. **Better Uptime** (Free tier):
   - Sign up at https://betteruptime.com
   - Monitor your `/healthz` endpoint
   - Get alerts for downtime

## Railway Configuration

Railway will use the provided `railway.toml` file for configuration. Key settings:

- **Builder**: Dockerfile
- **Health Check**: `/healthz` endpoint
- **Restart Policy**: On failure (max 3 retries)
- **Auto-deploy**: Enabled for main branch

## Cost Optimization

### Free Tier Limits

- **Railway**: $5/month credit (Hobby plan)
- **Neon**: 0.5GB storage, 3 databases
- **Upstash**: 10k commands/day, 256MB storage

### Tips to Stay Within Budget

1. **Enable caching** to reduce database queries
2. **Monitor usage** in each platform's dashboard
3. **Set up alerts** when approaching limits
4. **Optimize queries** to reduce database load
5. **Use Redis wisely** - cache frequently accessed data

## Troubleshooting

### Build Fails

1. Check Railway build logs
2. Verify Dockerfile syntax
3. Ensure all dependencies in requirements.txt

### Health Check Fails

1. Check if application is binding to `0.0.0.0:$PORT`
2. Verify `/healthz` endpoint is accessible
3. Check logs for startup errors

### Database Connection Issues

1. Verify `DATABASE_URL` is correct
2. Check if Neon database is active (auto-pauses after inactivity)
3. Verify SSL mode is set to `require`

### Redis Connection Issues

1. Verify `REDIS_URL` is correct
2. Check if using `rediss://` (TLS) protocol
3. Verify Upstash database is active

### Performance Issues

1. Monitor Railway metrics
2. Check database connection pool size
3. Verify caching is enabled
4. Check if hitting Neon/Upstash rate limits

## Scaling Up

When you need more resources:

1. **Railway**:
   - Upgrade to Pro plan ($20/month)
   - Increase memory/CPU limits

2. **Neon**:
   - Upgrade to paid tier for more storage/compute

3. **Upstash**:
   - Upgrade for more commands/storage

## Security Checklist

- [ ] `SECRET_KEY` is randomly generated and secure
- [ ] `DEBUG` is set to `false`
- [ ] `ENABLE_DETAILED_ERRORS` is `false`
- [ ] Database password is strong
- [ ] Redis is TLS-enabled (`rediss://`)
- [ ] CORS origins include only your frontend domains
- [ ] Environment variables are set in Railway (not in code)
- [ ] Sensitive data is never logged
- [ ] API documentation is accessible only when needed

## Rollback

If deployment fails:

1. Go to Railway dashboard
2. Click "Deployments"
3. Find previous successful deployment
4. Click "Redeploy"

## Support

- Railway: https://railway.app/help
- Neon: https://neon.tech/docs
- Upstash: https://docs.upstash.com

## Next Steps

After successful deployment:

1. Update frontend with API URL
2. Test all endpoints
3. Set up monitoring
4. Configure rate limiting
5. Implement remaining features
