# Render Deployment Checklist

Use this checklist to ensure smooth deployment to Render.

## Pre-Deployment Checklist

### ☐ Code Ready
- [x] Backend code committed to GitHub
- [x] Dockerfile exists in `backend/` directory
- [x] render.yaml configuration file created
- [x] All dependencies in requirements.txt
- [ ] Code pushed to GitHub main branch

### ☐ Free Tier Services Setup
- [ ] Neon PostgreSQL database created
  - [ ] Connection string saved (DATABASE_URL)
  - [ ] Database accessible from internet
- [ ] Upstash Redis created
  - [ ] Connection string saved (REDIS_URL)
  - [ ] TLS connection string obtained

### ☐ Environment Variables Ready
- [ ] DATABASE_URL (from Neon)
- [ ] REDIS_URL (from Upstash)  
- [ ] SECRET_KEY (will generate in Render)
- [ ] ENVIRONMENT=production
- [ ] LOG_LEVEL=INFO
- [ ] DEBUG=false
- [ ] CORS_ORIGINS set (can use ["*"] initially)

## Deployment Steps

### ☐ Step 1: GitHub Repository
- [ ] Create GitHub repository
- [ ] Push code to main branch
- [ ] Verify backend/ folder is at root

### ☐ Step 2: Render Setup
- [ ] Create Render account (https://render.com)
- [ ] Connect GitHub account
- [ ] Select repository

### ☐ Step 3: Service Configuration
- [ ] Name: chess-pattern-analyzer-api
- [ ] Region selected
- [ ] Root Directory: `backend`
- [ ] Runtime: Docker
- [ ] Plan: Free
- [ ] Health Check: /healthz

### ☐ Step 4: Environment Variables
- [ ] All environment variables added
- [ ] SECRET_KEY generated
- [ ] Database and Redis URLs pasted

### ☐ Step 5: Deploy
- [ ] Click "Create Web Service"
- [ ] Wait for build (5-10 minutes)
- [ ] Check logs for errors

## Post-Deployment Verification

### ☐ API Endpoints Working
```bash
# Replace YOUR_APP with your Render URL
export API_URL="https://your-app.onrender.com"

# Test health check
curl $API_URL/healthz

# Test readiness
curl $API_URL/api/v1/health/ready

# View API docs
open $API_URL/api/docs  # or visit in browser
```

### ☐ Expected Responses
- [ ] /healthz returns 200 {"status": "healthy"}
- [ ] /api/v1/health/ready returns readiness checks
- [ ] /api/docs shows Swagger UI
- [ ] No errors in Render logs

### ☐ Database Connectivity
- [ ] Readiness probe shows "database": "ready"
- [ ] No connection errors in logs

### ☐ Redis Connectivity  
- [ ] Readiness probe shows "redis": "ready"
- [ ] No Redis errors in logs

## Common Issues

### Build Fails
- [ ] Check Dockerfile path is correct
- [ ] Verify all files committed to GitHub
- [ ] Check build logs for specific errors

### Service Won't Start
- [ ] Verify all environment variables set
- [ ] Check DATABASE_URL format
- [ ] Check REDIS_URL format (should be rediss:// for TLS)
- [ ] Review startup logs

### Health Check Fails
- [ ] Verify /healthz path is correct
- [ ] Check if service actually started
- [ ] Review application logs

## URLs to Save

Once deployed, save these:

```
Backend API: https://_____________________.onrender.com
API Docs: https://_____________________.onrender.com/api/docs
Health Check: https://_____________________.onrender.com/healthz

Neon Dashboard: https://console.neon.tech
Upstash Dashboard: https://console.upstash.com  
Render Dashboard: https://dashboard.render.com
```

## Next Steps After Deployment

- [ ] Test API endpoints manually
- [ ] Deploy frontend to Vercel
- [ ] Update CORS_ORIGINS with frontend URL
- [ ] Test full integration
- [ ] Share with beta testers

## Upgrade Path (Future)

When ready to eliminate cold starts:

**Option 1: Render Starter ($7/month)**
- More RAM (2GB)
- No cold starts
- Better performance

**Option 2: Railway ($5/month)**
- Same RAM as free Render
- No cold starts
- Faster startup

Code works on both - just redeploy!

---

**Status**: Ready to deploy! 🚀

Follow the detailed guide in `RENDER_DEPLOYMENT_GUIDE.md`
