# Deployment_Link.md

# Live Application

## Application URL

**Live deployment URL:** `Not provided yet`

Add the actual public frontend URL here after deployment.

Example:

``` text
https://<your-frontend-domain>
```

## Backend API URL

**Backend API URL:** `Not provided yet`

Example:

``` text
https://<your-backend-domain>
```

## Deployment Configuration

The deployed application consists of:

-   React + Vite frontend
-   FastAPI backend
-   Python static-analysis engine
-   Gemini AI review integration

### Backend Environment Variables

``` text
GEMINI_API_KEY=<configured-secret>
GEMINI_MODEL=<configured-model>
```

Do not place the real Gemini API key in this file or commit it to Git.

## Pre-Submission Checklist

-   [ ] Frontend is publicly accessible
-   [ ] Backend API is publicly accessible
-   [ ] Frontend points to the production backend
-   [ ] Gemini secret is configured securely
-   [ ] `.env` is not committed
-   [ ] ZIP upload works
-   [ ] Public GitHub analysis works
-   [ ] Findings page works
-   [ ] Architecture page works
-   [ ] AI Review works when Gemini is configured
-   [ ] Performance metrics are displayed
-   [ ] Error handling works
