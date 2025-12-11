"""
Local testing script for the quiz solver
Run this to test your implementation locally
"""
import asyncio
import json
import httpx

from config import EMAIL, SECRET
from quiz_solver import QuizSolver, solve_quiz
from browser_handler import get_browser, close_browser
from llm_client import llm


async def test_browser():
    """Test browser functionality"""
    print("\n=== Testing Browser ===")
    browser = await get_browser()
    
    # Test with a simple page
    test_url = "https://httpbin.org/html"
    text, html = await browser.get_page_content(test_url)
    print(f"Text length: {len(text)}")
    print(f"HTML length: {len(html)}")
    print(f"Sample text: {text[:200]}...")
    
    await close_browser()
    print("✅ Browser test passed!")


async def test_llm():
    """Test LLM functionality"""
    print("\n=== Testing LLM ===")
    
    # Simple question
    response = llm.ask("What is 2 + 2? Reply with just the number.")
    print(f"2 + 2 = {response}")
    
    # Data extraction
    context = """
    | Name | Value |
    |------|-------|
    | A    | 10    |
    | B    | 20    |
    | C    | 30    |
    """
    response = llm.solve_quiz("What is the sum of all values?", context)
    print(f"Sum of values: {response}")
    
    print("✅ LLM test passed!")


async def test_demo_endpoint():
    """Test with the demo endpoint"""
    print("\n=== Testing Demo Endpoint ===")
    
    demo_url = "https://tds-llm-analysis.s-anand.net/demo"
    
    try:
        solver = QuizSolver(email=EMAIL, secret=SECRET)
        result = await solver.solve_and_submit(demo_url)
        
        print(f"Results: {json.dumps(result, indent=2, default=str)}")
        print("✅ Demo endpoint test completed!")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


async def test_server_locally():
    """Test the local server"""
    print("\n=== Testing Local Server ===")
    
    async with httpx.AsyncClient() as client:
        # Health check
        try:
            response = await client.get("http://localhost:8000/health")
            print(f"Health check: {response.json()}")
        except:
            print("❌ Server not running. Start with: python main.py")
            return
        
        # Test invalid JSON
        response = await client.post(
            "http://localhost:8000/",
            content="not json",
            headers={"Content-Type": "application/json"}
        )
        print(f"Invalid JSON response: {response.status_code} - {response.json()}")
        
        # Test invalid secret
        response = await client.post(
            "http://localhost:8000/",
            json={"email": "test@test.com", "secret": "wrong"}
        )
        print(f"Invalid secret response: {response.status_code} - {response.json()}")
        
        # Test valid request
        response = await client.post(
            "http://localhost:8000/",
            json={
                "email": EMAIL,
                "secret": SECRET,
                "url": "https://tds-llm-analysis.s-anand.net/demo"
            }
        )
        print(f"Valid request response: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2, default=str)}")
    
    print("✅ Local server test completed!")


async def main():
    """Run all tests"""
    print("🧪 LLM Analysis Quiz - Local Tests")
    print("="*50)
    
    # Test components
    await test_browser()
    await test_llm()
    
    # Optionally test demo endpoint
    # await test_demo_endpoint()
    
    # Test local server (uncomment when server is running)
    # await test_server_locally()
    
    print("\n✅ All tests completed!")


if __name__ == "__main__":
    asyncio.run(main())

