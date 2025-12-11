"""
Advanced Quiz Solver with specialized handlers for different question types
"""
import asyncio
import re
import json
import base64
import io
import hashlib
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urljoin, urlparse
import httpx
import pandas as pd
import numpy as np

from llm_client import llm
from browser_handler import get_browser
from data_processor import processor


class AdvancedQuizSolver:
    """Advanced quiz solver with specialized question handlers"""
    
    def __init__(self, email: str, secret: str):
        self.email = email
        self.secret = secret
        self.llm = llm
        self.processor = processor
        self.data_cache = {}  # Cache for downloaded data
    
    async def solve_quiz(self, quiz_url: str) -> Dict[str, Any]:
        """Main entry point"""
        print(f"[AdvancedSolver] Processing: {quiz_url}")
        
        # Get rendered page content
        browser = await get_browser()
        text_content, html_content, screenshot = await browser.get_page_with_screenshot(quiz_url)
        
        # Parse the page
        parsed = self._parse_quiz_page(text_content, html_content, quiz_url)
        question = parsed['question']
        submit_url = parsed['submit_url']
        resources = parsed['resources']
        
        print(f"[AdvancedSolver] Question: {question[:200]}...")
        print(f"[AdvancedSolver] Submit URL: {submit_url}")
        print(f"[AdvancedSolver] Resources: {len(resources)}")
        
        # Download and process resources
        data_context = await self._gather_resources(resources)
        
        # Detect question type and solve
        question_type = self._detect_question_type(question)
        print(f"[AdvancedSolver] Question type: {question_type}")
        
        # Solve based on type
        answer = await self._solve_by_type(question, question_type, data_context, screenshot)
        
        return {
            'answer': answer,
            'submit_url': submit_url,
            'question': question,
            'question_type': question_type
        }
    
    def _parse_quiz_page(self, text: str, html: str, base_url: str) -> Dict:
        """Parse quiz page to extract question, submit URL, and resources"""
        result = {
            'question': text,
            'submit_url': '',
            'resources': []
        }
        
        # Find submit URL
        submit_patterns = [
            r'(?:post|submit|send)\s+(?:your\s+)?(?:answer\s+)?to\s+[`"\']?(https?://[^\s<>"`\']+)[`"\']?',
            r'POST\s+to\s+[`"\']?(https?://[^\s<>"`\']+)[`"\']?',
            r'(https?://[^\s<>"`\']+/submit[^\s<>"`\']*)',
            r'(https?://[^\s<>"`\']+/answer[^\s<>"`\']*)',
            r'endpoint[:\s]+[`"\']?(https?://[^\s<>"`\']+)[`"\']?',
        ]
        
        for pattern in submit_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                result['submit_url'] = match.group(1).rstrip('.,;:')
                break
        
        if not result['submit_url']:
            for pattern in submit_patterns:
                match = re.search(pattern, html, re.IGNORECASE)
                if match:
                    result['submit_url'] = match.group(1).rstrip('.,;:')
                    break
        
        # Find resources (files, APIs, etc.)
        found_urls = set()
        
        # File links
        file_pattern = r'<a[^>]+href=["\']?([^"\'>\s]+)["\']?[^>]*>'
        for match in re.finditer(file_pattern, html, re.IGNORECASE):
            href = match.group(1)
            if any(ext in href.lower() for ext in ['.pdf', '.csv', '.xlsx', '.xls', '.json', '.txt', '.png', '.jpg', '.jpeg', '.gif']):
                full_url = urljoin(base_url, href)
                if full_url not in found_urls:
                    found_urls.add(full_url)
                    result['resources'].append({'url': full_url, 'type': 'file'})
        
        # Direct URLs in text
        url_pattern = r'(https?://[^\s<>"`\']+\.(?:pdf|csv|xlsx?|json|txt|png|jpe?g|gif))'
        for match in re.finditer(url_pattern, text, re.IGNORECASE):
            url = match.group(1).rstrip('.,;:')
            if url not in found_urls and result['submit_url'] not in url:
                found_urls.add(url)
                result['resources'].append({'url': url, 'type': 'file'})
        
        # API endpoints
        api_pattern = r'(https?://[^\s<>"`\']+/api/[^\s<>"`\']*)'
        for match in re.finditer(api_pattern, text + html, re.IGNORECASE):
            url = match.group(1).rstrip('.,;:')
            if url not in found_urls:
                found_urls.add(url)
                result['resources'].append({'url': url, 'type': 'api'})
        
        return result
    
    async def _gather_resources(self, resources: List[Dict]) -> str:
        """Download and process all resources"""
        context_parts = []
        
        for resource in resources:
            url = resource['url']
            rtype = resource.get('type', 'file')
            
            try:
                print(f"[AdvancedSolver] Fetching: {url}")
                content, content_type = await self.processor.fetch_url(url)
                file_type = self.processor.detect_file_type(content, content_type, url)
                
                print(f"[AdvancedSolver] Type: {file_type}, Size: {len(content)} bytes")
                
                if file_type == 'pdf':
                    pdf_data = self.processor.process_pdf(content)
                    context_parts.append(f"\n=== PDF from {url} ===")
                    context_parts.append(pdf_data['text'])
                    
                    # Also include tables in structured format
                    for i, table in enumerate(pdf_data.get('tables', [])):
                        context_parts.append(f"\n--- Table {i+1} on Page {table['page']} ---")
                        for row in table['data']:
                            context_parts.append(' | '.join(str(cell) for cell in row))
                
                elif file_type == 'csv':
                    df = self.processor.process_csv(content)
                    self.data_cache[url] = df
                    context_parts.append(f"\n=== CSV from {url} ===")
                    context_parts.append(self.processor.dataframe_to_context(df))
                
                elif file_type == 'excel':
                    df = self.processor.process_excel(content)
                    self.data_cache[url] = df
                    context_parts.append(f"\n=== Excel from {url} ===")
                    context_parts.append(self.processor.dataframe_to_context(df))
                
                elif file_type == 'json':
                    json_data = self.processor.process_json(content)
                    self.data_cache[url] = json_data
                    context_parts.append(f"\n=== JSON from {url} ===")
                    context_parts.append(json.dumps(json_data, indent=2))
                
                elif file_type == 'image':
                    img_data = self.processor.process_image(content)
                    self.data_cache[url] = img_data
                    context_parts.append(f"\n=== Image from {url} ===")
                    context_parts.append(f"[Image: {img_data['width']}x{img_data['height']} {img_data['format']}]")
                
                else:
                    try:
                        text = content.decode('utf-8')
                    except:
                        text = content.decode('latin-1', errors='ignore')
                    context_parts.append(f"\n=== Text from {url} ===")
                    context_parts.append(text[:10000])  # Limit text size
                    
            except Exception as e:
                print(f"[AdvancedSolver] Error fetching {url}: {e}")
                context_parts.append(f"\n=== Error fetching {url}: {e} ===")
        
        return '\n'.join(context_parts)
    
    def _detect_question_type(self, question: str) -> str:
        """Detect the type of question"""
        q_lower = question.lower()
        
        # Calculation types
        if any(word in q_lower for word in ['sum of', 'total', 'add up', 'combined']):
            return 'sum'
        if any(word in q_lower for word in ['average', 'mean', 'avg']):
            return 'average'
        if any(word in q_lower for word in ['count', 'how many', 'number of']):
            return 'count'
        if any(word in q_lower for word in ['maximum', 'max', 'highest', 'largest']):
            return 'max'
        if any(word in q_lower for word in ['minimum', 'min', 'lowest', 'smallest']):
            return 'min'
        if any(word in q_lower for word in ['median']):
            return 'median'
        if any(word in q_lower for word in ['standard deviation', 'std']):
            return 'std'
        
        # Filter/lookup types
        if any(word in q_lower for word in ['where', 'which', 'filter', 'find']):
            return 'filter'
        if any(word in q_lower for word in ['sort', 'order', 'rank']):
            return 'sort'
        if any(word in q_lower for word in ['group by', 'grouped', 'per']):
            return 'group'
        
        # Special types
        if any(word in q_lower for word in ['chart', 'plot', 'graph', 'visualiz', 'draw']):
            return 'visualization'
        if any(word in q_lower for word in ['image', 'picture', 'photo', 'screenshot']):
            return 'image'
        if any(word in q_lower for word in ['hash', 'md5', 'sha']):
            return 'hash'
        if any(word in q_lower for word in ['encode', 'base64']):
            return 'encode'
        
        return 'general'
    
    async def _solve_by_type(self, question: str, q_type: str, data_context: str, screenshot: bytes) -> Any:
        """Solve question based on detected type"""
        
        # Try pandas-based calculation for dataframes in cache
        if q_type in ['sum', 'average', 'count', 'max', 'min', 'median', 'std']:
            for url, data in self.data_cache.items():
                if isinstance(data, pd.DataFrame):
                    result = await self._calculate_from_dataframe(question, q_type, data)
                    if result is not None:
                        return result
        
        # For visualization, try to generate chart
        if q_type == 'visualization':
            for url, data in self.data_cache.items():
                if isinstance(data, pd.DataFrame):
                    chart_base64 = await self._generate_chart(question, data)
                    if chart_base64:
                        return f"data:image/png;base64,{chart_base64}"
        
        # Use LLM for general solving
        return self._llm_solve(question, data_context, screenshot)
    
    async def _calculate_from_dataframe(self, question: str, q_type: str, df: pd.DataFrame) -> Optional[Any]:
        """Try to calculate answer from dataframe"""
        # Extract column name from question
        q_lower = question.lower()
        
        # Find column mentioned in question
        target_column = None
        for col in df.columns:
            if col.lower() in q_lower or f'"{col}"' in question or f"'{col}'" in question:
                target_column = col
                break
        
        if not target_column:
            # Try fuzzy matching
            for col in df.columns:
                col_words = col.lower().split()
                if any(word in q_lower for word in col_words):
                    target_column = col
                    break
        
        if not target_column:
            return None
        
        try:
            col_data = pd.to_numeric(df[target_column], errors='coerce')
            
            if q_type == 'sum':
                return float(col_data.sum())
            elif q_type == 'average':
                return round(float(col_data.mean()), 2)
            elif q_type == 'count':
                return int(col_data.count())
            elif q_type == 'max':
                return float(col_data.max())
            elif q_type == 'min':
                return float(col_data.min())
            elif q_type == 'median':
                return float(col_data.median())
            elif q_type == 'std':
                return round(float(col_data.std()), 2)
        except Exception as e:
            print(f"[AdvancedSolver] Calculation error: {e}")
        
        return None
    
    async def _generate_chart(self, question: str, df: pd.DataFrame) -> Optional[str]:
        """Generate a chart based on the question"""
        try:
            import matplotlib
            matplotlib.use('Agg')
            import matplotlib.pyplot as plt
            
            # Determine chart type from question
            q_lower = question.lower()
            
            fig, ax = plt.subplots(figsize=(10, 6))
            
            if 'bar' in q_lower:
                if len(df.columns) >= 2:
                    df.plot(kind='bar', x=df.columns[0], y=df.columns[1], ax=ax)
            elif 'line' in q_lower:
                df.plot(kind='line', ax=ax)
            elif 'pie' in q_lower:
                if len(df.columns) >= 2:
                    df.set_index(df.columns[0])[df.columns[1]].plot(kind='pie', ax=ax)
            elif 'scatter' in q_lower:
                if len(df.columns) >= 2:
                    df.plot(kind='scatter', x=df.columns[0], y=df.columns[1], ax=ax)
            elif 'hist' in q_lower:
                df.plot(kind='hist', ax=ax)
            else:
                # Default to bar chart
                if len(df.columns) >= 2:
                    df.head(20).plot(kind='bar', x=df.columns[0], y=df.columns[1], ax=ax)
                else:
                    df.head(20).plot(kind='bar', ax=ax)
            
            plt.tight_layout()
            
            buf = io.BytesIO()
            plt.savefig(buf, format='png', dpi=100, bbox_inches='tight')
            buf.seek(0)
            plt.close(fig)
            
            return base64.b64encode(buf.getvalue()).decode()
        except Exception as e:
            print(f"[AdvancedSolver] Chart generation error: {e}")
            return None
    
    def _llm_solve(self, question: str, data_context: str, screenshot: bytes) -> Any:
        """Use LLM to solve the question"""
        prompt = f"""
You are an expert data analyst. Solve this quiz question.

QUESTION:
{question}

DATA CONTEXT:
{data_context[:50000]}  # Limit context size

INSTRUCTIONS:
1. Analyze the data carefully
2. Perform any required calculations
3. Return ONLY the final answer value
4. No explanations, no units, no additional text
5. For numbers: just the number (e.g., 42 or 3.14)
6. For text: just the text
7. For boolean: true or false (lowercase)
8. For JSON: valid JSON only

YOUR ANSWER (just the value):
"""
        
        response = self.llm.ask(prompt)
        return self._parse_answer(response)
    
    def _parse_answer(self, response: str) -> Any:
        """Parse and clean the answer"""
        if not response:
            return None
        
        response = response.strip()
        
        # Remove markdown code blocks
        if response.startswith('```'):
            lines = response.split('\n')
            if lines[-1].strip() == '```':
                response = '\n'.join(lines[1:-1])
            else:
                response = '\n'.join(lines[1:])
            response = response.strip()
        
        # Remove quotes
        if (response.startswith('"') and response.endswith('"')) or \
           (response.startswith("'") and response.endswith("'")):
            response = response[1:-1]
        
        # Try JSON first
        try:
            result = json.loads(response)
            # Validate it's serializable
            json.dumps(result)
            return result
        except (json.JSONDecodeError, TypeError):
            pass
        
        # Try number
        try:
            clean = re.sub(r'[^\d.\-e]', '', response)
            if clean:
                if '.' in clean or 'e' in clean.lower():
                    return float(clean)
                return int(clean)
        except:
            pass
        
        # Boolean
        if response.lower() == 'true':
            return True
        if response.lower() == 'false':
            return False
        
        # Return as string for text answers
        return response.strip()
    
    async def submit_answer(self, submit_url: str, quiz_url: str, answer: Any) -> Dict:
        """Submit answer to the quiz"""
        payload = {
            "email": self.email,
            "secret": self.secret,
            "url": quiz_url,
            "answer": answer
        }
        
        print(f"[AdvancedSolver] Submitting to: {submit_url}")
        print(f"[AdvancedSolver] Answer type: {type(answer).__name__}")
        print(f"[AdvancedSolver] Answer preview: {str(answer)[:100]}")
        
        async with httpx.AsyncClient(timeout=60) as client:
            try:
                response = await client.post(submit_url, json=payload)
                
                print(f"[AdvancedSolver] Response status: {response.status_code}")
                
                try:
                    return response.json()
                except:
                    return {"error": response.text, "status_code": response.status_code}
            except Exception as e:
                print(f"[AdvancedSolver] Submission error: {e}")
                return {"error": str(e), "submission_failed": True}
    
    async def solve_and_submit(self, quiz_url: str) -> Dict:
        """Main method: solve and submit quiz chain"""
        results = []
        current_url = quiz_url
        max_attempts = 20
        
        for i in range(max_attempts):
            print(f"\n{'='*60}")
            print(f"[AdvancedSolver] Quiz {i+1}: {current_url}")
            print(f"{'='*60}")
            
            try:
                # Clear data cache for each quiz
                self.data_cache = {}
                
                # Solve
                solution = await self.solve_quiz(current_url)
                
                if not solution.get('submit_url'):
                    results.append({
                        'quiz_url': current_url,
                        'error': 'No submit URL found',
                        'solution': solution
                    })
                    break
                
                # Submit
                response = await self.submit_answer(
                    solution['submit_url'],
                    current_url,
                    solution['answer']
                )
                
                result = {
                    'quiz_url': current_url,
                    'question': solution.get('question', '')[:200],
                    'question_type': solution.get('question_type'),
                    'answer': solution['answer'],
                    'response': response
                }
                results.append(result)
                
                print(f"[AdvancedSolver] Correct: {response.get('correct', 'unknown')}")
                
                # Check for next URL
                next_url = response.get('url')
                if next_url:
                    current_url = next_url
                else:
                    print("[AdvancedSolver] Quiz chain complete!")
                    break
                    
            except Exception as e:
                print(f"[AdvancedSolver] Error: {e}")
                import traceback
                traceback.print_exc()
                results.append({
                    'quiz_url': current_url,
                    'error': str(e)
                })
                break
        
        return {'results': results}

