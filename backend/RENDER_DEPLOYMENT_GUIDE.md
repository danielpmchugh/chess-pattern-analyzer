# Render Deployment Guide - Chess Pattern Analyzer

This guide walks you through deploying the Chess Pattern Analyzer backend to Render's **free tier**.

## Prerequisites

- GitHub account
- Render account (free) - Sign up at https://render.com
- Neon PostgreSQL database (free) - https://neon.tech
- Upstash Redis (free) - https://upstash.com

## Step 1: Set Up Free Database Services

### 1.1 Create Neon PostgreSQL Database (FREE)

1. Go to https://neon.tech and sign up/login
2. Click **"Create a project"**
3. Project settings:
   - Name: `chess-analyzer`
   - PostgreSQL version: 16
   - Region: Choose closest to you
4. Click **"Create project"**
5. **Copy the connection string** - it looks like:
   ```
   postgresql://username:password@ep-xxx.us-east-2.aws.neon.tech/neondb
   ```
6. Save this for later - we'll use it as `DATABASE_URL`

### 1.2 Create Upstash Redis (FREE)

1. Go to https://upstash.com and sign up/login
2. Click **"Create database"**
3. Database settings:
   - Name: `chess-analyzer-cache`
   - Type: Regional
   - Region: Choose closest to you
4. Click **"Create"**
5. Go to **Details** tab
6. **Copy the connection string** (TLS format):
   ```
   rediss://default:xxxxx@us1-xxx.upstash.io:6379
   ```
7. Save this for later - we'll use it as `REDIS_URL`

## Step 2: Push Code to GitHub

If you haven't already:

```bash
cd /home/gspadz/github/chess
git init
git add .
git commit -m "Initial commit: Chess Pattern Analyzer backend"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/chess-pattern-analyzer.git
git push -u origin main
```

## Step 3: Deploy to Render

### 3.1 Connect GitHub Repository

1. Go to https://dashboard.render.com
2. Click **"New +"** → **"Web Service"**
3. Connect your GitHub account if not already connected
4. Find and select your `chess-pattern-analyzer` repository
5. Click **"Connect"**

### 3.2 Configure Web Service

Fill in the deployment settings:

**Basic Settings:**
- **Name**: `chess-pattern-analyzer-api` (or your choice)
- **Region**: Choose closest to your users
- **Branch**: `main`
- **Root Directory**: `backend`
- **Runtime**: `Docker`
- **Plan**: **Free** ✓

**Build & Deploy:**
- **Dockerfile Path**: `./Dockerfile` (default)
- **Docker Build Context Directory**: `.` (default)

### 3.3 Add Environment Variables

Click **"Advanced"** → **"Add Environment Variable"** and add these:

| Key | Value | Notes |
|-----|-------|-------|
| `ENVIRONMENT` | `production` | |
| `LOG_LEVEL` | `INFO` | |
| `DEBUG` | `false` | |
| `DATABASE_URL` | `postgresql://...` | Paste your Neon connection string |
| `REDIS_URL` | `rediss://...` | Paste your Upstash connection string |
| `SECRET_KEY` | Click "Generate" | Use Render's generate button |
| `CORS_ORIGINS` | `["*"]` | Update with frontend URL later |
| `CACHE_ENABLED` | `true` | |
| `CACHE_TTL` | `43200` | 12 hours in seconds |

### 3.4 Health Check

- **Health Check Path**: `/healthz`
- Leave other settings as default

### 3.5 Deploy!

1. Click **"Create Web Service"**
2. Render will now:
   - Pull your code from GitHub
   - Build the Docker image
   - Deploy the container
   - Assign a URL: `https://chess-pattern-analyzer-api.onrender.com`

**Initial deployment takes 5-10 minutes.**

## Step 4: Verify Deployment

### 4.1 Check Build Logs

1. Click on your service in Render dashboard
2. Go to **"Logs"** tab
3. Watch for:
   ```
   ==> Deploying...
   ==> Build successful
   ==> Starting service...
   ==> Your service is live 🎉
   ```

### 4.2 Test the API

Once deployed, test these endpoints:

**Health Check:**
```bash
curl https://your-app.onrender.com/healthz
```

Expected response:
```json
{
  "status": "healthy",
  "service": "chess-pattern-analyzer"
}
```

**API Documentation:**
Visit: `https://your-app.onrender.com/api/docs`

You should see the Swagger UI with all API endpoints!

### 4.3 Test Readiness Probe

```bash
curl https://your-app.onrender.com/api/v1/health/ready
```

Should return:
```json
{
  "status": "ready",
  "checks": {
    "api": "ready",
    "redis": "ready",
    "database": "ready"
  }
}
```

## Step 5: Update Frontend CORS (Later)

Once you deploy your frontend to Vercel:

1. Go to Render dashboard
2. Click your web service
3. Go to **"Environment"** tab
4. Update `CORS_ORIGINS`:
   ```
   ["https://your-frontend.vercel.app"]
   ```
5. Click **"Save Changes"**
6. Service will redeploy automatically

## Understanding Render Free Tier

### What You Get (FREE)
- 512MB RAM
- Shared CPU
- Automatic HTTPS
- Auto-deploy from GitHub
- Build minutes: 750 hours/month (plenty)

### Important Limitations
- **Cold starts**: Service spins down after 15 minutes of inactivity
- **First request**: Takes 30-50 seconds to wake up
- **Subsequent requests**: Normal speed (~200-500ms)

### Cold Start Behavior
```
No traffic for 15 min → Service sleeps
First request → Wake up (30-50s) → Response
Next requests → Fast responses
```

This is **perfect for MVP** - your users won't mind the occasional wait.

## Troubleshooting

### Build Fails

**Error: "Can't find Dockerfile"**
- Check "Root Directory" is set to `backend`
- Verify Dockerfile exists in `backend/` folder

**Error: "Build ran out of memory"**
- Reduce Docker image size (already optimized in our Dockerfile)
- Upgrade to paid plan if needed ($7/month for 2GB RAM)

### Service Won't Start

**Check logs for:**
```bash
# In Render dashboard → Logs tab
```

Common issues:
- Missing environment variables
- Database connection failed (check DATABASE_URL)
- Redis connection failed (check REDIS_URL)

### Health Check Failing

1. Verify `/healthz` endpoint works locally:
   ```bash
   docker build -t chess-api .
   docker run -p 8000:8000 chess-api
   curl http://localhost:8000/healthz
   ```

2. Check Render logs for startup errors

### Database Connection Issues

**Error: "Could not connect to database"**

Verify your Neon connection string:
- Should start with `postgresql://`
- Should include password
- Should end with database name

Test locally:
```bash
export DATABASE_URL="your-neon-url"
python3 -c "import asyncpg; print('OK')"
```

## Monitoring Your App

### View Logs
1. Render Dashboard → Your Service → **Logs** tab
2. See real-time logs
3. Filter by log level (INFO, ERROR, etc.)

### Monitor Health
1. Render Dashboard → Your Service → **Metrics** tab
2. See:
   - Request count
   - Response times
   - Memory usage
   - CPU usage

### Set Up Alerts (Optional)
1. Render Dashboard → Your Service → **Settings**
2. Add email for deploy notifications
3. Get notified of build failures

## Cost Breakdown

| Service | Plan | Cost |
|---------|------|------|
| Render Web Service | Free | $0/month |
| Neon PostgreSQL | Free (0.5GB) | $0/month |
| Upstash Redis | Free (10k cmds/day) | $0/month |
| **Total** | | **$0/month** 🎉 |

## Next Steps

1. ✅ Backend deployed to Render
2. ⏭️ Deploy frontend to Vercel (FRONTEND-001)
3. ⏭️ Update CORS_ORIGINS with frontend URL
4. ⏭️ Test end-to-end flow
5. ⏭️ Share with beta users!

## Upgrading Later

When you're ready to upgrade (more traffic, no cold starts):

**Render Starter Plan ($7/month):**
- 2GB RAM
- No cold starts
- Better performance

**Or switch to Railway ($5/month):**
- 512MB RAM (same as free Render)
- No cold starts
- Faster cold start recovery

Your code works on both - just change deployment target!

## Support

- Render Docs: https://render.com/docs
- Render Community: https://community.render.com
- This project: https://github.com/YOUR_USERNAME/chess-pattern-analyzer/issues

---

**Ready to deploy?** Follow the steps above and your backend will be live in ~10 minutes! 🚀
