# Deployment Guide - LLM Analysis Quiz Solver

This guide covers how to deploy your API endpoint for the LLM Analysis Quiz evaluation.

## Prerequisites

- GitHub repository with MIT LICENSE
- Environment variables configured
- API endpoint with HTTPS URL (required for production)

## Option 1: Railway (Recommended)

Railway is simple, free tier available, and perfect for this use case.

### Steps:

1. **Prepare your GitHub repository**
   - Make sure code is committed and pushed
   - Ensure `.env` is in `.gitignore` (not committed)
   - Verify MIT LICENSE file exists

2. **Create Railway account**
   - Go to https://railway.app
   - Sign up with GitHub

3. **Create new project**
   - Click "New Project"
   - Select "Deploy from GitHub repo"
   - Authorize and select your repository

4. **Configure environment variables**
   - In Railway dashboard, go to Variables
   - Add the following:
     ```
     EMAIL=your-email@example.com
     SECRET=your_secret_key
     GEMINI_API_KEY=your_gemini_api_key
     PORT=8000
     ```

5. **Deploy**
   - Railway will automatically detect Python and deploy
   - Your endpoint URL will be shown (e.g., `https://your-app-xyz.railway.app`)

6. **Test**
   ```bash
   curl -X POST https://your-app-xyz.railway.app/ \
     -H "Content-Type: application/json" \
     -d '{
       "email": "your@email.com",
       "secret": "your_secret",
       "url": "https://tds-llm-analysis.s-anand.net/demo"
     }'
   ```

## Option 2: Render

### Steps:

1. **Connect GitHub to Render**
   - Go to https://render.com
   - Sign up and connect GitHub

2. **Create Web Service**
   - New → Web Service
   - Select your repository
   - Configure:
     - Name: `tds-llm-quiz`
     - Runtime: Python 3.11
     - Build command: `pip install -r requirements.txt && playwright install chromium`
     - Start command: `uvicorn main:app --host 0.0.0.0 --port $PORT`

3. **Add environment variables**
   - In Render dashboard:
     - EMAIL
     - SECRET
     - GEMINI_API_KEY

4. **Deploy**
   - Click "Create Web Service"
   - Render will deploy automatically
   - Your URL will be shown

## Option 3: Vercel (with Serverless)

### Steps:

1. **Create `vercel.json`**
   ```json
   {
     "buildCommand": "pip install -r requirements.txt && playwright install chromium",
     "installCommand": "pip install -r requirements.txt",
     "env": {
       "PYTHONUNBUFFERED": "1"
     },
     "functions": {
       "main.py": {
         "runtime": "python3.11"
       }
     }
   }
   ```

2. **Deploy**
   ```bash
   vercel --prod
   ```

## Option 4: Docker (Local or Cloud)

### Build locally:
```bash
docker build -t tds-llm-quiz .
docker run \
  -e EMAIL=your@email.com \
  -e SECRET=your_secret \
  -e GEMINI_API_KEY=your_key \
  -p 8000:8000 \
  tds-llm-quiz
```

### Deploy to cloud:
- Push Docker image to Docker Hub or cloud registry
- Deploy to AWS, Google Cloud, Azure, etc.

## Verification Checklist

Before submitting your endpoint URL:

- [ ] Server is running and accessible via HTTPS
- [ ] Health check works: `curl https://your-endpoint/health`
- [ ] Returns HTTP 200 for valid secret
- [ ] Returns HTTP 403 for invalid secret
- [ ] Returns HTTP 400 for invalid JSON
- [ ] Can process quiz URLs from demo endpoint
- [ ] Responses include proper JSON format
- [ ] Can submit answers successfully

## Testing Your Deployment

### Test health check:
```bash
curl https://your-endpoint/health
# Expected: HTTP 200, {"status":"ok","message":"Server is healthy"}
```

### Test invalid JSON:
```bash
curl -X POST https://your-endpoint/ \
  -H "Content-Type: application/json" \
  -d '{invalid}'
# Expected: HTTP 400
```

### Test invalid secret:
```bash
curl -X POST https://your-endpoint/ \
  -H "Content-Type: application/json" \
  -d '{"email":"test@test.com","secret":"wrong","url":"http://test.com"}'
# Expected: HTTP 403
```

### Test valid request:
```bash
curl -X POST https://your-endpoint/ \
  -H "Content-Type: application/json" \
  -d '{
    "email":"your@email.com",
    "secret":"YOUR_SECRET",
    "url":"https://tds-llm-analysis.s-anand.net/demo"
  }'
# Expected: HTTP 200, processing results
```

## URL Requirements

The endpoint URL you submit:
- MUST be HTTPS (http only for local testing)
- MUST handle POST requests to `/`
- MUST be publicly accessible
- Examples:
  - ✓ `https://your-domain.com/`
  - ✓ `https://your-app-xyz.railway.app/`
  - ✓ `https://your-app.onrender.com/`
  - ✗ `http://localhost:8000/` (not public)
  - ✗ `https://your-domain.com/api` (wrong path)

## Troubleshooting

### Endpoint not responding
- Check server logs: `railway logs` or equivalent
- Verify environment variables are set
- Check GEMINI_API_KEY is valid

### Timeout errors
- Check browser/LLM timeout settings in config.py
- Ensure Playwright is properly installed
- Verify internet connectivity

### 403 errors
- Double-check SECRET matches exactly
- Ensure no extra spaces or special characters in SECRET

### Large payload errors
- Check answer format isn't too large
- Strip unnecessary data from responses
- Limit visualization sizes if generating images

## Security Notes

1. **Never commit `.env`** - Use environment variables in deployment platform
2. **Rotate secrets regularly** - Create new secret after submission if needed
3. **Use HTTPS only** - Never submit HTTP endpoint for production
4. **Limit API key exposure** - Don't share GEMINI_API_KEY
5. **Review logs for sensitive data** - Don't log email/secret values

## Support

- Check the README.md for general information
- Review test_endpoint.py for implementation details
- Check server logs for specific errors
- Verify all environment variables are set correctly

---

**Expected Evaluation Window**: Sat 29 Nov 2025, 3:00 pm - 4:00 pm IST
**Endpoint Availability**: 1 hour
**Maximum response time**: 3 minutes per quiz
