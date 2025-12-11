"""
Simple script to run the server
"""
import uvicorn
from config import HOST, PORT

if __name__ == "__main__":
    print(f"""
╔══════════════════════════════════════════════════════════════╗
║            LLM Analysis Quiz Solver v1.0.0                   ║
╠══════════════════════════════════════════════════════════════╣
║  Starting server on http://{HOST}:{PORT}                      
║                                                              ║
║  Endpoints:                                                  ║
║  - POST /        : Main quiz handler                         ║
║  - POST /webhook : Alternative webhook                       ║
║  - POST /quiz    : Alternative quiz endpoint                 ║
║  - GET /         : Health check                              ║
║  - GET /health   : Health check                              ║
╚══════════════════════════════════════════════════════════════╝
""")
    
    uvicorn.run(
        "main:app",
        host=HOST,
        port=PORT,
        reload=True,
        log_level="info"
    )

