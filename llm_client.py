"""
Gemini LLM Client for quiz solving
"""
import google.generativeai as genai
import base64
import json
import re
from typing import Optional, Union, Any
from config import GEMINI_API_KEY, GEMINI_MODEL, MAX_TOKENS, TEMPERATURE

# Configure Gemini
genai.configure(api_key=GEMINI_API_KEY)

class GeminiClient:
    def __init__(self):
        self.model = genai.GenerativeModel(
            model_name=GEMINI_MODEL,
            generation_config={
                "temperature": TEMPERATURE,
                "max_output_tokens": MAX_TOKENS,
                "response_mime_type": "text/plain"
            }
        )
        self.vision_model = genai.GenerativeModel(
            model_name="gemini-2.0-flash",
            generation_config={
                "temperature": TEMPERATURE,
                "max_output_tokens": MAX_TOKENS
            }
        )
    
    def ask(self, prompt: str, context: str = "") -> str:
        """Ask Gemini a question with optional context"""
        full_prompt = f"{context}\n\n{prompt}" if context else prompt
        try:
            response = self.model.generate_content(full_prompt)
            if response and response.text:
                return response.text
            return ""
        except Exception as e:
            print(f"[LLM] Error: {e}")
            import traceback
            traceback.print_exc()
            return ""
    
    def analyze_image(self, image_data: bytes, prompt: str, mime_type: str = "image/png") -> str:
        """Analyze an image with a prompt"""
        try:
            image_part = {
                "mime_type": mime_type,
                "data": base64.b64encode(image_data).decode()
            }
            response = self.vision_model.generate_content([prompt, image_part])
            return response.text
        except Exception as e:
            print(f"Vision Error: {e}")
            return ""
    
    def analyze_image_base64(self, base64_data: str, prompt: str, mime_type: str = "image/png") -> str:
        """Analyze a base64-encoded image"""
        try:
            # Remove data URL prefix if present
            if "," in base64_data:
                base64_data = base64_data.split(",")[1]
            image_part = {
                "mime_type": mime_type,
                "data": base64_data
            }
            response = self.vision_model.generate_content([prompt, image_part])
            return response.text
        except Exception as e:
            print(f"Vision Error: {e}")
            return ""
    
    def extract_answer(self, question: str, context: str, answer_type: str = "auto") -> Any:
        """Extract a specific type of answer from the context"""
        type_instructions = {
            "number": "Extract ONLY the numerical answer. Return just the number, nothing else.",
            "string": "Extract ONLY the text answer. Return just the text, nothing else.",
            "boolean": "Return ONLY 'true' or 'false', nothing else.",
            "json": "Return ONLY valid JSON, nothing else.",
            "auto": "Determine the answer type and return the most appropriate format."
        }
        
        prompt = f"""
Based on the following context, answer the question.

CONTEXT:
{context}

QUESTION:
{question}

INSTRUCTION: {type_instructions.get(answer_type, type_instructions['auto'])}

Return ONLY the answer value with no explanation or additional text.
"""
        response = self.ask(prompt)
        return self._parse_answer(response.strip(), answer_type)
    
    def _parse_answer(self, response: str, answer_type: str) -> Any:
        """Parse the response into the appropriate type"""
        response = response.strip()
        
        # Remove markdown code blocks if present
        if response.startswith("```"):
            lines = response.split("\n")
            response = "\n".join(lines[1:-1]) if lines[-1] == "```" else "\n".join(lines[1:])
            response = response.strip()
        
        if answer_type == "number":
            # Extract number from response
            numbers = re.findall(r'-?\d+\.?\d*', response)
            if numbers:
                num = numbers[0]
                return int(float(num)) if '.' not in num else float(num)
            return response
        
        elif answer_type == "boolean":
            response_lower = response.lower()
            if "true" in response_lower:
                return True
            elif "false" in response_lower:
                return False
            return response
        
        elif answer_type == "json":
            try:
                return json.loads(response)
            except:
                return response
        
        return response
    
    def solve_quiz(self, question: str, data_context: str = "", images: list = None) -> Any:
        """Main method to solve a quiz question"""
        prompt = f"""
You are an expert data analyst and quiz solver. Solve the following quiz question.

QUESTION:
{question}

{"DATA/CONTEXT:" + chr(10) + data_context if data_context else ""}

IMPORTANT INSTRUCTIONS:
1. Analyze the question carefully
2. If calculations are needed, show your work mentally but only return the final answer
3. Return ONLY the final answer value - no explanations, no units, no additional text
4. For numbers, return just the number (e.g., 42 or 3.14)
5. For text, return just the text
6. For boolean, return true or false
7. For JSON, return valid JSON

YOUR ANSWER (just the value):
"""
        
        if images:
            # Use vision model for image-based questions
            parts = [prompt]
            for img_data, mime_type in images:
                parts.append({
                    "mime_type": mime_type,
                    "data": base64.b64encode(img_data).decode() if isinstance(img_data, bytes) else img_data
                })
            try:
                response = self.vision_model.generate_content(parts)
                return self._clean_answer(response.text)
            except Exception as e:
                print(f"Vision solve error: {e}")
                return None
        else:
            response = self.ask(prompt)
            return self._clean_answer(response)
    
    def _clean_answer(self, response: str) -> Any:
        """Clean and parse the answer response"""
        if not response:
            return None
        
        response = response.strip()
        
        # Remove markdown formatting
        if response.startswith("```"):
            lines = response.split("\n")
            if lines[-1].strip() == "```":
                response = "\n".join(lines[1:-1])
            else:
                response = "\n".join(lines[1:])
            response = response.strip()
        
        # Try to parse as JSON
        try:
            return json.loads(response)
        except:
            pass
        
        # Try to parse as number
        try:
            if '.' in response:
                return float(response)
            return int(response)
        except:
            pass
        
        # Check for boolean
        if response.lower() in ['true', 'false']:
            return response.lower() == 'true'
        
        return response


# Global client instance
llm = GeminiClient()

