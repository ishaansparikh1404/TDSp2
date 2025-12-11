#!/bin/bash
echo "============================================"
echo "LLM Analysis Quiz Solver - Setup Script"
echo "============================================"
echo

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python3 is not installed"
    exit 1
fi

echo "[1/4] Creating virtual environment..."
python3 -m venv venv
source venv/bin/activate

echo "[2/4] Installing Python dependencies..."
pip install -r requirements.txt

echo "[3/4] Installing Playwright browsers..."
playwright install chromium

echo "[4/4] Setup complete!"
echo
echo "============================================"
echo "To start the server, run:"
echo "  source venv/bin/activate"
echo "  python main.py"
echo "============================================"
echo
echo "Or use: python run_server.py"

