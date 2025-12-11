"""
LLM Analysis Quiz - Main FastAPI Server
Handles incoming quiz requests and orchestrates solving
"""
import asyncio
import json
import traceback
import time
from contextlib import asynccontextmanager
from typing import Any, Dict, Optional

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from config import SECRET, EMAIL, HOST, PORT, REQUEST_TIMEOUT
from advanced_solver import AdvancedQuizSolver
from browser_handler import close_browser


# Lifespan manager for startup/shutdown
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("[SERVER] Starting LLM Analysis Quiz Server...")
    print(f"[SERVER] Email: {EMAIL}")
    print(f"[SERVER] Secret: {'***' + SECRET[-4:] if len(SECRET) > 4 else '****'}")
    yield
    # Shutdown
    print("[SERVER] Shutting down...")
    await close_browser()


# Create FastAPI app
app = FastAPI(
    title="LLM Analysis Quiz Solver",
    description="API endpoint for solving LLM-based quiz questions",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """Health check endpoint"""
    return JSONResponse(
        status_code=200,
        content={
            "status": "ok",
            "message": "LLM Analysis Quiz Solver is running!"
        }
    )


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return JSONResponse(
        status_code=200,
        content={
            "status": "ok",
            "message": "Server is healthy"
        }
    )


async def process_quiz_request(request: Request):
    """
    Main endpoint for receiving quiz tasks
    HTTP Status Codes per spec:
    - 400: Invalid JSON
    - 403: Invalid secret
    - 200: Valid request (success or error during solving)
    """
    request_start = time.time()
    
    # Parse JSON body - return 400 for invalid JSON
    try:
        body = await request.json()
    except json.JSONDecodeError as e:
        return JSONResponse(
            status_code=400,
            content={"status": "error", "message": f"Invalid JSON: {str(e)}"}
        )
    except Exception as e:
        return JSONResponse(
            status_code=400,
            content={"status": "error", "message": f"Invalid request: {str(e)}"}
        )
    
    # Validate it's a dictionary
    if not isinstance(body, dict):
        return JSONResponse(
            status_code=400,
            content={"status": "error", "message": "Request body must be a JSON object"}
        )
    
    # Extract fields
    email = body.get("email")
    secret = body.get("secret")
    url = body.get("url")
    
    # Verify secret - return 403 for invalid/missing secret
    if not secret or secret != SECRET:
        return JSONResponse(
            status_code=403,
            content={"status": "error", "message": "Invalid secret"}
        )
    
    # If no URL, just acknowledge successful authentication
    if not url:
        return JSONResponse(
            status_code=200,
            content={"status": "ok", "message": "Secret verified. No quiz URL provided."}
        )
    
    # Process the quiz
    print(f"\n{'='*60}")
    print(f"[QUIZ] Received quiz request")
    print(f"[QUIZ] Email: {email}")
    print(f"[QUIZ] URL: {url}")
    print(f"{'='*60}\n")
    
    try:
        # Create solver and process quiz within timeout
        solver = AdvancedQuizSolver(email=email, secret=secret)
        result = await asyncio.wait_for(
            solver.solve_and_submit(url),
            timeout=REQUEST_TIMEOUT
        )
        
        elapsed = time.time() - request_start
        print(f"[OK] Quiz processed in {elapsed:.2f}s")
        
        return JSONResponse(
            status_code=200,
            content={
                "status": "ok",
                "message": "Quiz processed",
                "results": result.get("results", [])
            }
        )
    
    except asyncio.TimeoutError:
        print(f"[TIMEOUT] Timeout after {REQUEST_TIMEOUT}s")
        return JSONResponse(
            status_code=200,
            content={"status": "timeout", "message": f"Exceeded {REQUEST_TIMEOUT}s timeout"}
        )
    
    except Exception as e:
        print(f"[ERROR] Error: {e}")
        traceback.print_exc()
        return JSONResponse(
            status_code=200,
            content={"status": "error", "message": f"Error: {str(e)}"}
        )


# Route all POST endpoints to the handler
@app.post("/")
async def main_endpoint(request: Request):
    return await process_quiz_request(request)

@app.post("/webhook")
async def webhook_endpoint(request: Request):
    return await process_quiz_request(request)

@app.post("/quiz")
async def quiz_endpoint(request: Request):
    return await process_quiz_request(request)

@app.post("/api/quiz")
async def api_quiz_endpoint(request: Request):
    return await process_quiz_request(request)


if __name__ == "__main__":
    import uvicorn
    
    print(f"""
================================================================
           LLM Analysis Quiz Solver v1.0.0
================================================================
  Server: http://{HOST}:{PORT}
  Timeout: {REQUEST_TIMEOUT}s
  
  Endpoints:
  - POST /         : Main quiz handler
  - POST /webhook  : Webhook endpoint
  - GET  /health   : Health check
================================================================
""")
    
    uvicorn.run("main:app", host=HOST, port=PORT, reload=False, log_level="info")
