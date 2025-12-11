#!/usr/bin/env python3
"""
Test script for the LLM Analysis Quiz endpoint
Tests the implementation against the spec requirements
"""
import asyncio
import json
import httpx
import sys
from pathlib import Path

# Load environment
import os
from dotenv import load_dotenv

load_dotenv()

# Configuration
ENDPOINT_URL = os.getenv("ENDPOINT_URL", "http://localhost:8000")
DEMO_URL = "https://tds-llm-analysis.s-anand.net/demo"
EMAIL = os.getenv("EMAIL", "")
SECRET = os.getenv("SECRET", "")

async def test_health_check():
    """Test 1: Health check endpoint"""
    print("\n" + "="*60)
    print("TEST 1: Health Check")
    print("="*60)
    
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(f"{ENDPOINT_URL}/health")
            print(f"Status: {response.status_code}")
            print(f"Response: {response.json()}")
            
            assert response.status_code == 200, f"Expected 200, got {response.status_code}"
            assert response.json()["status"] == "ok"
            print("✓ PASS: Health check working")
            return True
    except Exception as e:
        print(f"✗ FAIL: {e}")
        return False


async def test_invalid_json():
    """Test 2: Invalid JSON (should return 400)"""
    print("\n" + "="*60)
    print("TEST 2: Invalid JSON (expect HTTP 400)")
    print("="*60)
    
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            # Send invalid JSON
            response = await client.post(
                f"{ENDPOINT_URL}/",
                content="{ invalid json }",
                headers={"content-type": "application/json"}
            )
            print(f"Status: {response.status_code}")
            print(f"Response: {response.text[:200]}")
            
            assert response.status_code == 400, f"Expected 400, got {response.status_code}"
            print("✓ PASS: Invalid JSON returns 400")
            return True
    except Exception as e:
        print(f"✗ FAIL: {e}")
        return False


async def test_invalid_secret():
    """Test 3: Invalid secret (should return 403)"""
    print("\n" + "="*60)
    print("TEST 3: Invalid Secret (expect HTTP 403)")
    print("="*60)
    
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(
                f"{ENDPOINT_URL}/",
                json={
                    "email": "test@example.com",
                    "secret": "wrong_secret_12345",
                    "url": "https://example.com/quiz"
                }
            )
            print(f"Status: {response.status_code}")
            print(f"Response: {response.json()}")
            
            assert response.status_code == 403, f"Expected 403, got {response.status_code}"
            print("✓ PASS: Invalid secret returns 403")
            return True
    except Exception as e:
        print(f"✗ FAIL: {e}")
        return False


async def test_valid_secret_no_url():
    """Test 4: Valid secret with no URL (should return 200)"""
    print("\n" + "="*60)
    print("TEST 4: Valid Secret, No URL (expect HTTP 200)")
    print("="*60)
    
    if not EMAIL or not SECRET:
        print("⊘ SKIP: EMAIL or SECRET not configured")
        return None
    
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(
                f"{ENDPOINT_URL}/",
                json={
                    "email": EMAIL,
                    "secret": SECRET
                }
            )
            print(f"Status: {response.status_code}")
            print(f"Response: {response.json()}")
            
            assert response.status_code == 200, f"Expected 200, got {response.status_code}"
            print("✓ PASS: Valid secret with no URL returns 200")
            return True
    except Exception as e:
        print(f"✗ FAIL: {e}")
        return False


async def test_demo_endpoint():
    """Test 5: Test with demo endpoint"""
    print("\n" + "="*60)
    print("TEST 5: Demo Endpoint Test")
    print("="*60)
    
    if not EMAIL or not SECRET:
        print("⊘ SKIP: EMAIL or SECRET not configured")
        return None
    
    try:
        print(f"Testing with demo URL: {DEMO_URL}")
        
        async with httpx.AsyncClient(timeout=180) as client:
            response = await client.post(
                f"{ENDPOINT_URL}/",
                json={
                    "email": EMAIL,
                    "secret": SECRET,
                    "url": DEMO_URL
                }
            )
            print(f"Status: {response.status_code}")
            result = response.json()
            
            # Check basic structure
            assert response.status_code == 200
            assert "status" in result
            
            # Print results
            if "results" in result:
                for i, res in enumerate(result["results"]):
                    print(f"\nQuiz {i+1}:")
                    print(f"  - Status: {res.get('quiz_url', 'N/A')[:50]}...")
                    if "answer" in res:
                        print(f"  - Answer: {res['answer']}")
                    if "error" in res:
                        print(f"  - Error: {res['error']}")
                    if "response" in res:
                        resp = res["response"]
                        if isinstance(resp, dict):
                            print(f"  - Correct: {resp.get('correct', 'unknown')}")
            
            print("\n✓ PASS: Demo endpoint test completed")
            return True
    except asyncio.TimeoutError:
        print("✗ FAIL: Demo endpoint test timed out (>180s)")
        return False
    except Exception as e:
        print(f"✗ FAIL: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_missing_secret():
    """Test 6: Missing secret field (should return 403)"""
    print("\n" + "="*60)
    print("TEST 6: Missing Secret Field (expect HTTP 403)")
    print("="*60)
    
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(
                f"{ENDPOINT_URL}/",
                json={
                    "email": "test@example.com",
                    "url": "https://example.com/quiz"
                }
            )
            print(f"Status: {response.status_code}")
            print(f"Response: {response.json()}")
            
            assert response.status_code == 403, f"Expected 403, got {response.status_code}"
            print("✓ PASS: Missing secret returns 403")
            return True
    except Exception as e:
        print(f"✗ FAIL: {e}")
        return False


async def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("LLM Analysis Quiz - Endpoint Tests")
    print("="*60)
    print(f"Endpoint: {ENDPOINT_URL}")
    print(f"Email: {EMAIL}")
    print(f"Secret: {'***' + SECRET[-4:] if SECRET else 'NOT SET'}")
    
    results = []
    
    # Run tests
    results.append(("Health Check", await test_health_check()))
    results.append(("Invalid JSON (400)", await test_invalid_json()))
    results.append(("Invalid Secret (403)", await test_invalid_secret()))
    results.append(("Missing Secret (403)", await test_missing_secret()))
    results.append(("Valid Secret, No URL (200)", await test_valid_secret_no_url()))
    results.append(("Demo Endpoint", await test_demo_endpoint()))
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    passed = 0
    failed = 0
    skipped = 0
    
    for test_name, result in results:
        if result is None:
            status = "SKIP"
            skipped += 1
        elif result:
            status = "PASS"
            passed += 1
        else:
            status = "FAIL"
            failed += 1
        print(f"{status:5} | {test_name}")
    
    print(f"\nTotal: {passed} passed, {failed} failed, {skipped} skipped")
    
    if failed > 0:
        print("\n⚠️  Some tests failed. Please check the output above.")
        return 1
    else:
        print("\n✓ All tests passed!")
        return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
