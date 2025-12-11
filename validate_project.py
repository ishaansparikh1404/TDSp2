#!/usr/bin/env python3
"""
Project validation script - Checks all requirements are met
"""
import os
import json
import sys
from pathlib import Path

def check_file_exists(filepath, description):
    """Check if a file exists"""
    if os.path.exists(filepath):
        print(f"✓ {description}")
        return True
    else:
        print(f"✗ {description} - MISSING")
        return False

def check_file_contains(filepath, text, description):
    """Check if a file contains specific text"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            if text in content:
                print(f"✓ {description}")
                return True
            else:
                print(f"✗ {description} - NOT FOUND")
                return False
    except Exception as e:
        print(f"✗ {description} - ERROR: {e}")
        return False

def validate_python_syntax(filepath):
    """Check Python syntax"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            compile(f.read(), filepath, 'exec')
        return True
    except SyntaxError as e:
        print(f"  Syntax error: {e}")
        return False
    except Exception as e:
        print(f"  Error: {e}")
        return False

def main():
    print("\n" + "="*60)
    print("LLM Analysis Quiz - Project Validation")
    print("="*60 + "\n")
    
    checks_passed = 0
    checks_failed = 0
    
    # Core application files
    print("Core Application Files:")
    core_files = [
        ("main.py", "Main FastAPI server"),
        ("config.py", "Configuration management"),
        ("advanced_solver.py", "Advanced quiz solver"),
        ("quiz_solver.py", "Quiz solving logic"),
        ("browser_handler.py", "Playwright browser automation"),
        ("llm_client.py", "Gemini LLM client"),
        ("data_processor.py", "Data processing utilities"),
    ]
    
    for filepath, description in core_files:
        if check_file_exists(filepath, description):
            checks_passed += 1
            if filepath.endswith('.py'):
                if validate_python_syntax(filepath):
                    print(f"  └─ Syntax: OK")
                else:
                    print(f"  └─ Syntax: INVALID")
                    checks_failed += 1
        else:
            checks_failed += 1
    
    # Configuration files
    print("\nConfiguration Files:")
    config_files = [
        ("requirements.txt", "Python dependencies"),
        ("Dockerfile", "Docker configuration"),
        (".gitignore", "Git ignore rules"),
        (".env.example", "Environment template"),
        ("LICENSE", "MIT License"),
    ]
    
    for filepath, description in config_files:
        if check_file_exists(filepath, description):
            checks_passed += 1
        else:
            checks_failed += 1
    
    # Documentation files
    print("\nDocumentation Files:")
    docs_files = [
        ("README.md", "Main documentation"),
        ("SETUP_GUIDE.md", "Setup and submission guide"),
        ("DEPLOYMENT.md", "Deployment instructions"),
        ("FINAL_CHECKLIST.md", "Pre-submission checklist"),
        ("IMPLEMENTATION_SUMMARY.md", "Implementation summary"),
    ]
    
    for filepath, description in docs_files:
        if check_file_exists(filepath, description):
            checks_passed += 1
        else:
            checks_failed += 1
    
    # Testing files
    print("\nTesting Files:")
    test_files = [
        ("test_endpoint.py", "Endpoint test script"),
    ]
    
    for filepath, description in test_files:
        if check_file_exists(filepath, description):
            checks_passed += 1
        else:
            checks_failed += 1
    
    # Content verification
    print("\nContent Verification:")
    
    # Check for hardcoded credentials
    print("  Checking for hardcoded credentials in main files...")
    checks = [
        ("main.py", "SECRET =", "Hardcoded SECRET in main.py", True),  # Should NOT contain
        ("config.py", 'os.getenv("SECRET"', "Correct SECRET loading in config", False),  # Should contain
        ("config.py", 'os.getenv("EMAIL"', "Correct EMAIL loading in config", False),  # Should contain
        ("config.py", 'os.getenv("GEMINI_API_KEY"', "Correct API key loading", False),  # Should contain
    ]
    
    for filepath, text, description, should_not_contain in checks:
        if should_not_contain:
            # These files should NOT contain this text
            try:
                with open(filepath, 'r') as f:
                    content = f.read()
                    if text not in content:
                        print(f"✓ {description}")
                        checks_passed += 1
                    else:
                        print(f"✗ {description} - FOUND (should not be there)")
                        checks_failed += 1
            except:
                pass
        else:
            # These files SHOULD contain this text
            if check_file_contains(filepath, text, description):
                checks_passed += 1
            else:
                checks_failed += 1
    
    # Check API status codes
    print("\nAPI Specification Checks:")
    if check_file_contains("main.py", "status_code=400", "HTTP 400 for invalid JSON"):
        checks_passed += 1
    else:
        checks_failed += 1
    
    if check_file_contains("main.py", "status_code=403", "HTTP 403 for invalid secret"):
        checks_passed += 1
    else:
        checks_failed += 1
    
    if check_file_contains("main.py", "status_code=200", "HTTP 200 for valid requests"):
        checks_passed += 1
    else:
        checks_failed += 1
    
    if check_file_contains("config.py", "REQUEST_TIMEOUT = 180", "3-minute timeout configured"):
        checks_passed += 1
    else:
        checks_failed += 1
    
    if check_file_contains("main.py", "asyncio.wait_for", "Timeout management in place"):
        checks_passed += 1
    else:
        checks_failed += 1
    
    # Check for .env in gitignore
    print("\nSecurity Checks:")
    if check_file_contains(".gitignore", ".env", ".env excluded from git"):
        checks_passed += 1
    else:
        checks_failed += 1
    
    # Check for license
    if check_file_contains("LICENSE", "MIT License", "MIT License present"):
        checks_passed += 1
    else:
        checks_failed += 1
    
    # Summary
    print("\n" + "="*60)
    print("VALIDATION SUMMARY")
    print("="*60)
    print(f"✓ Passed: {checks_passed}")
    print(f"✗ Failed: {checks_failed}")
    
    if checks_failed == 0:
        print("\n🎉 All checks passed! Project is ready for submission.")
        return 0
    else:
        print(f"\n⚠️  {checks_failed} check(s) failed. Please fix the issues above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
