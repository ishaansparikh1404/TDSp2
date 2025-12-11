"""
Helper script to start ngrok tunnel for public URL
Run this AFTER starting main.py to get a public HTTPS URL
"""
import subprocess
import sys
import time

def check_ngrok():
    """Check if ngrok is installed"""
    try:
        result = subprocess.run(['ngrok', 'version'], capture_output=True, text=True)
        return result.returncode == 0
    except FileNotFoundError:
        return False

def start_ngrok(port=8000):
    """Start ngrok tunnel"""
    print(f"""
╔══════════════════════════════════════════════════════════════╗
║              Starting ngrok tunnel...                        ║
╠══════════════════════════════════════════════════════════════╣
║  Make sure your server is running on port {port}              
║                                                              ║
║  The public URL will appear in the ngrok interface.          ║
║  Use that URL for the Google Form submission.                ║
║                                                              ║
║  Press Ctrl+C to stop the tunnel.                            ║
╚══════════════════════════════════════════════════════════════╝
""")
    
    try:
        subprocess.run(['ngrok', 'http', str(port)])
    except KeyboardInterrupt:
        print("\nTunnel stopped.")

def main():
    if not check_ngrok():
        print("""
ngrok is not installed!

To install ngrok:
1. Go to https://ngrok.com/download
2. Download for your OS
3. Extract and add to PATH
4. Run: ngrok config add-authtoken YOUR_TOKEN

Alternative: Use a cloud platform like Railway, Render, or Heroku.
""")
        sys.exit(1)
    
    port = 8000
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except ValueError:
            pass
    
    start_ngrok(port)

if __name__ == "__main__":
    main()

