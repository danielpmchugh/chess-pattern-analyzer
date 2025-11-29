# Vercel Deployment Guide

This guide will walk you through deploying the Chess Pattern Analyzer frontend to Vercel.

## Prerequisites

- GitHub account (with the chess-pattern-analyzer repository)
- Vercel account (free tier is sufficient)

## Deployment Steps

### 1. Sign Up / Log In to Vercel

1. Go to [https://vercel.com](https://vercel.com)
2. Click "Sign Up" or "Log In"
3. Choose "Continue with GitHub" for the easiest integration

### 2. Import Your Project

1. From the Vercel dashboard, click "Add New..." → "Project"
2. You'll see a list of your GitHub repositories
3. Find `chess-pattern-analyzer` and click "Import"

### 3. Configure Project Settings

Vercel will auto-detect that this is a Next.js project. Configure these settings:

**Framework Preset:** Next.js (auto-detected)

**Root Directory:** `frontend` (IMPORTANT: Click "Edit" and set this to `frontend`)

**Build Command:** `npm run build` (auto-detected)

**Output Directory:** `.next` (auto-detected)

**Install Command:** `npm install` (auto-detected)

### 4. Set Environment Variables

Click "Environment Variables" and add:

- **Key:** `NEXT_PUBLIC_API_URL`
- **Value:** `https://chess-pattern-analyzer.onrender.com`
- **Environments:** Production, Preview, Development (check all)

### 5. Deploy

1. Click "Deploy"
2. Vercel will build and deploy your application
3. This typically takes 1-2 minutes

### 6. Verify Deployment

Once deployment completes:

1. You'll see a "Congratulations" screen
2. Click "Visit" to open your deployed site
3. Your site will be available at: `https://chess-pattern-analyzer.vercel.app` (or similar)

### 7. Test the Application

1. Enter a Chess.com username (e.g., "magnuscarlsen", "hikaru")
2. Click "Analyze My Games"
3. Wait for the analysis to complete (may take 30-60 seconds on first request due to Render cold start)
4. Verify the results display correctly

## Post-Deployment Tasks

### Update Backend CORS Settings

Your backend needs to allow requests from your new Vercel domain:

1. Go to your Render dashboard
2. Navigate to your `chess-pattern-analyzer-api` service
3. Go to "Environment" tab
4. Add a new environment variable:
   - **Key:** `CORS_ORIGINS`
   - **Value:** `https://your-vercel-url.vercel.app,http://localhost:3000`
   - Replace `your-vercel-url` with your actual Vercel deployment URL
5. Click "Save Changes"
6. Your backend will automatically redeploy

### Set Up Custom Domain (Optional)

1. In Vercel dashboard, go to your project
2. Click "Settings" → "Domains"
3. Add your custom domain
4. Follow the DNS configuration instructions
5. Update the `CORS_ORIGINS` on Render to include your custom domain

## Automatic Deployments

Vercel automatically deploys:

- **Production:** Every push to `main` branch
- **Preview:** Every pull request gets a unique preview URL

## Monitoring and Logs

- **Analytics:** Vercel provides free analytics in the "Analytics" tab
- **Logs:** Check deployment and function logs in the "Deployments" tab
- **Performance:** Monitor Core Web Vitals in the "Speed Insights" tab

## Troubleshooting

### Build Fails

- Check the build logs in Vercel dashboard
- Verify the root directory is set to `frontend`
- Ensure environment variables are set correctly

### API Requests Fail

- Check that `NEXT_PUBLIC_API_URL` is set correctly
- Verify CORS is configured on the backend
- Check browser console for CORS errors

### Backend Returns Errors

- Verify the backend is running: https://chess-pattern-analyzer.onrender.com/healthz
- Check that the Chess.com username is valid
- Note: First request may be slow due to Render's free tier cold start

## Cost

- **Vercel Free Tier Includes:**
  - Unlimited deployments
  - 100GB bandwidth per month
  - Automatic HTTPS
  - Global CDN
  - Preview deployments
  - Analytics

Perfect for your MVP with zero monthly cost!

## Next Steps

After successful deployment:

1. Update the main README.md with the live URL
2. Share your app with friends to test
3. Monitor usage in Vercel analytics
4. Consider adding more features from your roadmap

## Support

- Vercel Documentation: https://vercel.com/docs
- Vercel Support: https://vercel.com/support
- Next.js Documentation: https://nextjs.org/docs
