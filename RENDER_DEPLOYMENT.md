# Render Deployment Guide

## Option 1: Two Separate Services (Recommended)

Deploy backend and frontend as two separate web services.

### Backend Service
1. Create a new Web Service on Render
2. Connect your GitHub repository
3. Configure:
   - **Name**: `finance-tracker-backend`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `cd backend && uvicorn main:app --host 0.0.0.0 --port $PORT`
   - **Environment Variables**:
     - `SUPABASE_URL` = your_supabase_url
     - `SUPABASE_KEY` = your_supabase_anon_key
     - `JWT_SECRET_KEY` = your_random_secret_key
     - `GOOGLE_CLIENT_ID` = your_google_client_id (optional)
     - `GOOGLE_CLIENT_SECRET` = your_google_client_secret (optional)

4. Note the backend URL (e.g., `https://finance-tracker-backend.onrender.com`)

### Frontend Service
1. Create another Web Service on Render
2. Connect the same GitHub repository
3. Configure:
   - **Name**: `finance-tracker-frontend`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `cd frontend && streamlit run app.py --server.port $PORT --server.address 0.0.0.0`
   - **Environment Variables**:
     - `BACKEND_URL` = `https://finance-tracker-backend.onrender.com` (from step 4 above)

## Option 2: Single Service (Simple but Limited)

Deploy using the included `render.yaml` file for automatic configuration.

1. Push your code to GitHub
2. On Render Dashboard, click "New" → "Blueprint"
3. Connect your repository
4. Render will detect `render.yaml` and create both services automatically
5. Add environment variables for each service

## Option 3: Backend Only (Use Locally)

If you want to deploy only the backend API:

1. Create a Web Service on Render
2. Use these settings:
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `cd backend && uvicorn main:app --host 0.0.0.0 --port $PORT`
3. Add all backend environment variables
4. Update your local `frontend/app.py` to use the deployed backend URL

## Important Notes

### Python Version
Make sure your Render service uses Python 3.11 or 3.12 (not 3.13) for better compatibility.
- In Render dashboard, go to Environment and set Python Version

### Free Tier Limitations
- Services spin down after 15 minutes of inactivity
- First request after spin-down may take 30-60 seconds
- Consider upgrading for production use

### Environment Variables Required

**Backend (.env variables)**:
```
SUPABASE_URL=your_supabase_project_url
SUPABASE_KEY=your_supabase_anon_key
JWT_SECRET_KEY=your_random_secret_key_min_32_chars
GOOGLE_CLIENT_ID=optional_google_oauth_client_id
GOOGLE_CLIENT_SECRET=optional_google_oauth_secret
```

**Frontend**:
```
BACKEND_URL=https://your-backend-service.onrender.com
```

### Troubleshooting Build Failures

1. **Pandas build error**: Make sure using Python 3.11 or 3.12
2. **Missing dependencies**: Check requirements.txt is in root
3. **Port binding error**: Ensure using `$PORT` in start command
4. **Health check failing**: Backend must respond at `/health` endpoint

## After Deployment

1. Test backend: `https://your-backend.onrender.com/health`
2. Test API docs: `https://your-backend.onrender.com/docs`
3. Access frontend: `https://your-frontend.onrender.com`

## Updating Your App

```bash
git add .
git commit -m "Your update message"
git push
```

Render will automatically redeploy on every push to your main branch.
