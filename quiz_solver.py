"""
Main quiz solver logic - handles parsing questions and generating answers
"""
import asyncio
import re
import json
import base64
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urljoin, urlparse
import httpx

from llm_client import llm, GeminiClient
from browser_handler import get_browser, BrowserHandler
from data_processor import processor, DataProcessor
from config import EMAIL, SECRET


class QuizSolver:
    """Main quiz solver that orchestrates all components"""
    
    def __init__(self, email: str = None, secret: str = None):
        self.email = email or EMAIL
        self.secret = secret or SECRET
        self.llm = llm
        self.processor = processor
    
    async def solve_quiz(self, quiz_url: str) -> Dict[str, Any]:
        """
        Main entry point - fetches quiz page and solves it
        Returns dict with 'answer' and 'submit_url'
        """
        print(f"[QuizSolver] Fetching quiz from: {quiz_url}")
        
        # Get the quiz page content (JavaScript-rendered)
        browser = await get_browser()
        text_content, html_content = await browser.get_page_content(quiz_url)
        
        print(f"[QuizSolver] Page content length: {len(text_content)}")
        print(f"[QuizSolver] Content preview: {text_content[:500]}...")
        
        # Parse the question and submission URL
        question, submit_url, additional_urls = self._parse_quiz_page(text_content, html_content, quiz_url)
        
        print(f"[QuizSolver] Question: {question}")
        print(f"[QuizSolver] Submit URL: {submit_url}")
        print(f"[QuizSolver] Additional URLs: {additional_urls}")
        
        # Gather additional data if needed
        data_context = ""
        images = []
        
        for url_info in additional_urls:
            url = url_info['url']
            print(f"[QuizSolver] Fetching additional data from: {url}")
            
            try:
                content, content_type = await self.processor.fetch_url(url)
                file_type = self.processor.detect_file_type(content, content_type, url)
                
                print(f"[QuizSolver] File type: {file_type}, Size: {len(content)} bytes")
                
                if file_type == 'pdf':
                    pdf_data = self.processor.process_pdf(content)
                    data_context += f"\n\n=== PDF Content ===\n{pdf_data['text']}"
                    if pdf_data['tables']:
                        data_context += f"\n\n=== PDF Tables ===\n"
                        for table_info in pdf_data['tables']:
                            data_context += f"\nPage {table_info['page']}:\n"
                            for row in table_info['data']:
                                data_context += str(row) + "\n"
                
                elif file_type == 'csv':
                    df = self.processor.process_csv(content)
                    data_context += f"\n\n=== CSV Data ===\n{self.processor.dataframe_to_context(df)}"
                
                elif file_type == 'excel':
                    df = self.processor.process_excel(content)
                    data_context += f"\n\n=== Excel Data ===\n{self.processor.dataframe_to_context(df)}"
                
                elif file_type == 'json':
                    json_data = self.processor.process_json(content)
                    data_context += f"\n\n=== JSON Data ===\n{json.dumps(json_data, indent=2)}"
                
                elif file_type == 'image':
                    img_data = self.processor.process_image(content)
                    images.append((content, f"image/{img_data['format']}"))
                    data_context += f"\n\n=== Image ===\n[Image: {img_data['width']}x{img_data['height']} {img_data['format']}]"
                
                elif file_type == 'html':
                    # Might be another web page to scrape
                    html_text, html_full = await browser.get_page_content(url)
                    data_context += f"\n\n=== Web Page Content ===\n{html_text}"
                
                else:
                    # Plain text
                    try:
                        text = content.decode('utf-8')
                    except:
                        text = content.decode('latin-1')
                    data_context += f"\n\n=== Text Content ===\n{text}"
            
            except Exception as e:
                print(f"[QuizSolver] Error fetching {url}: {e}")
        
        # Solve the question using LLM
        print(f"[QuizSolver] Solving with LLM...")
        answer = await self._solve_question(question, data_context, images, html_content)
        
        print(f"[QuizSolver] Answer: {answer}")
        
        return {
            'answer': answer,
            'submit_url': submit_url,
            'question': question
        }
    
    def _parse_quiz_page(self, text_content: str, html_content: str, base_url: str) -> Tuple[str, str, List[Dict]]:
        """
        Parse the quiz page to extract:
        - The question text
        - The submission URL
        - Any additional URLs (files to download, APIs to call)
        """
        question = text_content
        submit_url = ""
        additional_urls = []
        
        # Find submission URL - look for patterns like "Post your answer to URL"
        submit_patterns = [
            r'(?:post|submit|send)\s+(?:your\s+)?answer\s+to\s+(https?://[^\s<>"]+)',
            r'(?:POST|Submit)\s+to\s+(https?://[^\s<>"]+)',
            r'submit\s+.*?(https?://[^\s<>"]+/submit[^\s<>"]*)',
            r'(https?://[^\s<>"]+/submit[^\s<>"]*)',
            r'(https?://[^\s<>"]+/answer[^\s<>"]*)',
        ]
        
        for pattern in submit_patterns:
            match = re.search(pattern, text_content, re.IGNORECASE)
            if match:
                submit_url = match.group(1).rstrip('.')
                break
        
        # Also check HTML for submit URL
        if not submit_url:
            html_submit_patterns = [
                r'(?:post|submit|send)\s+(?:your\s+)?answer\s+to\s+["\']?(https?://[^\s<>"\']+)',
                r'action=["\']?(https?://[^\s<>"\']+)["\']?',
            ]
            for pattern in html_submit_patterns:
                match = re.search(pattern, html_content, re.IGNORECASE)
                if match:
                    submit_url = match.group(1).rstrip('.')
                    break
        
        # Find file download URLs
        file_patterns = [
            r'<a\s+[^>]*href=["\']?(https?://[^\s<>"\']+\.(?:pdf|csv|xlsx?|json|txt|png|jpg|jpeg|gif))["\']?[^>]*>',
            r'(?:download|file|data)\s+(?:from\s+)?["\']?(https?://[^\s<>"\']+\.(?:pdf|csv|xlsx?|json|txt|png|jpg|jpeg|gif))["\']?',
            r'(https?://[^\s<>"\']+\.(?:pdf|csv|xlsx?|json|txt|png|jpg|jpeg|gif))',
        ]
        
        found_urls = set()
        for pattern in file_patterns:
            matches = re.findall(pattern, html_content, re.IGNORECASE)
            for match in matches:
                url = match if isinstance(match, str) else match[0]
                if url not in found_urls and submit_url not in url:
                    found_urls.add(url)
                    additional_urls.append({'url': url, 'type': 'file'})
        
        # Find API URLs
        api_patterns = [
            r'(?:api|endpoint|url)\s*[:\s]+\s*["\']?(https?://[^\s<>"\']+)["\']?',
            r'(?:call|fetch|get)\s+(?:from\s+)?["\']?(https?://[^\s<>"\']+api[^\s<>"\']*)["\']?',
        ]
        
        for pattern in api_patterns:
            matches = re.findall(pattern, text_content, re.IGNORECASE)
            for match in matches:
                url = match if isinstance(match, str) else match[0]
                if url not in found_urls and submit_url not in url:
                    found_urls.add(url)
                    additional_urls.append({'url': url, 'type': 'api'})
        
        # Also look for relative URLs in links
        href_pattern = r'<a\s+[^>]*href=["\']?([^"\'\s>]+)["\']?[^>]*>'
        for match in re.findall(href_pattern, html_content, re.IGNORECASE):
            if match.startswith('/') or not match.startswith(('http', '#', 'javascript')):
                full_url = urljoin(base_url, match)
                if full_url not in found_urls and full_url != base_url:
                    found_urls.add(full_url)
                    additional_urls.append({'url': full_url, 'type': 'link'})
        
        return question, submit_url, additional_urls
    
    async def _solve_question(self, question: str, data_context: str, images: List[Tuple[bytes, str]], html_content: str) -> Any:
        """Use LLM to solve the question"""
        
        # Check for specific question types and handle accordingly
        question_lower = question.lower()
        
        # Sum calculation
        if 'sum' in question_lower:
            answer = await self._try_calculate_sum(question, data_context)
            if answer is not None:
                return answer
        
        # Count calculation
        if 'count' in question_lower or 'how many' in question_lower:
            answer = await self._try_calculate_count(question, data_context)
            if answer is not None:
                return answer
        
        # Average calculation
        if 'average' in question_lower or 'mean' in question_lower:
            answer = await self._try_calculate_average(question, data_context)
            if answer is not None:
                return answer
        
        # Chart/visualization generation
        if any(word in question_lower for word in ['chart', 'plot', 'graph', 'visualiz', 'image']):
            answer = await self._try_generate_chart(question, data_context)
            if answer is not None:
                return answer
        
        # General LLM solving
        return self.llm.solve_quiz(question, data_context, images if images else None)
    
    async def _try_calculate_sum(self, question: str, data_context: str) -> Optional[Any]:
        """Try to calculate a sum from the data"""
        # Extract column name from question
        column_match = re.search(r'(?:sum\s+of\s+(?:the\s+)?["\']?)(\w+)["\']?(?:\s+column)?', question, re.IGNORECASE)
        if not column_match:
            column_match = re.search(r'["\'](\w+)["\']?\s+column', question, re.IGNORECASE)
        
        if column_match:
            column_name = column_match.group(1)
            
            # Try to extract numerical values from context
            prompt = f"""
From the following data, calculate the sum of the "{column_name}" column.

DATA:
{data_context}

Return ONLY the numerical sum, nothing else. If you need to sum values, add them up precisely.
"""
            result = self.llm.ask(prompt)
            try:
                # Clean the result
                result = result.strip()
                result = re.sub(r'[^\d.\-]', '', result)
                if '.' in result:
                    return float(result)
                return int(result)
            except:
                pass
        
        return None
    
    async def _try_calculate_count(self, question: str, data_context: str) -> Optional[Any]:
        """Try to calculate a count from the data"""
        prompt = f"""
Based on the following data, answer the counting question.

DATA:
{data_context}

QUESTION:
{question}

Return ONLY the count as a number, nothing else.
"""
        result = self.llm.ask(prompt)
        try:
            result = result.strip()
            result = re.sub(r'[^\d]', '', result)
            return int(result)
        except:
            return None
    
    async def _try_calculate_average(self, question: str, data_context: str) -> Optional[Any]:
        """Try to calculate an average from the data"""
        prompt = f"""
Based on the following data, calculate the average/mean requested.

DATA:
{data_context}

QUESTION:
{question}

Return ONLY the numerical average, nothing else. Round to 2 decimal places if needed.
"""
        result = self.llm.ask(prompt)
        try:
            result = result.strip()
            result = re.sub(r'[^\d.\-]', '', result)
            return float(result)
        except:
            return None
    
    async def _try_generate_chart(self, question: str, data_context: str) -> Optional[str]:
        """Try to generate a chart and return as base64"""
        # This is a placeholder - actual implementation would parse the data
        # and generate appropriate charts using matplotlib
        return None
    
    async def submit_answer(self, submit_url: str, quiz_url: str, answer: Any) -> Dict[str, Any]:
        """Submit the answer to the quiz"""
        payload = {
            "email": self.email,
            "secret": self.secret,
            "url": quiz_url,
            "answer": answer
        }
        
        print(f"[QuizSolver] Submitting to {submit_url}")
        print(f"[QuizSolver] Payload: {json.dumps(payload, indent=2)}")
        
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(submit_url, json=payload)
            
            print(f"[QuizSolver] Response status: {response.status_code}")
            print(f"[QuizSolver] Response: {response.text}")
            
            try:
                return response.json()
            except:
                return {"error": response.text, "status_code": response.status_code}
    
    async def solve_and_submit(self, quiz_url: str) -> Dict[str, Any]:
        """Solve a quiz and submit the answer, handling chains"""
        results = []
        current_url = quiz_url
        max_iterations = 20  # Safety limit
        
        for i in range(max_iterations):
            print(f"\n[QuizSolver] === Solving quiz {i+1}: {current_url} ===")
            
            try:
                # Solve the quiz
                solution = await self.solve_quiz(current_url)
                
                if not solution.get('submit_url'):
                    print("[QuizSolver] No submit URL found!")
                    results.append({
                        'quiz_url': current_url,
                        'error': 'No submit URL found',
                        'solution': solution
                    })
                    break
                
                # Submit the answer
                response = await self.submit_answer(
                    solution['submit_url'],
                    current_url,
                    solution['answer']
                )
                
                results.append({
                    'quiz_url': current_url,
                    'question': solution.get('question', '')[:200],
                    'answer': solution['answer'],
                    'response': response
                })
                
                # Check if there's a next URL
                if response.get('url'):
                    current_url = response['url']
                else:
                    print("[QuizSolver] No more quizzes!")
                    break
            
            except Exception as e:
                print(f"[QuizSolver] Error: {e}")
                import traceback
                traceback.print_exc()
                results.append({
                    'quiz_url': current_url,
                    'error': str(e)
                })
                break
        
        return {'results': results}


# Helper function for simple usage
async def solve_quiz(quiz_url: str, email: str = None, secret: str = None) -> Dict[str, Any]:
    """Simple function to solve a quiz"""
    solver = QuizSolver(email, secret)
    return await solver.solve_and_submit(quiz_url)

