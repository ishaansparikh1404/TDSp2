"""
Data processing utilities for various file types and data formats
"""
import io
import re
import json
import csv
import base64
from typing import Any, Dict, List, Optional, Union
import httpx
from PIL import Image
import pandas as pd
import numpy as np

# PDF processing
try:
    import pdfplumber
    HAS_PDFPLUMBER = True
except ImportError:
    HAS_PDFPLUMBER = False

try:
    import PyPDF2
    HAS_PYPDF2 = True
except ImportError:
    HAS_PYPDF2 = False

# Excel processing
try:
    import openpyxl
    HAS_OPENPYXL = True
except ImportError:
    HAS_OPENPYXL = False


class DataProcessor:
    """Universal data processor for various file types"""
    
    @staticmethod
    async def fetch_url(url: str, headers: dict = None) -> tuple[bytes, str]:
        """Fetch content from a URL"""
        async with httpx.AsyncClient(timeout=60, follow_redirects=True) as client:
            response = await client.get(url, headers=headers or {})
            response.raise_for_status()
            content_type = response.headers.get('content-type', 'application/octet-stream')
            return response.content, content_type
    
    @staticmethod
    def detect_file_type(content: bytes, content_type: str = "", url: str = "") -> str:
        """Detect file type from content, content-type header, or URL"""
        # Check URL extension
        url_lower = url.lower()
        if url_lower.endswith('.pdf'):
            return 'pdf'
        elif url_lower.endswith('.csv'):
            return 'csv'
        elif url_lower.endswith(('.xlsx', '.xls')):
            return 'excel'
        elif url_lower.endswith('.json'):
            return 'json'
        elif url_lower.endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp')):
            return 'image'
        elif url_lower.endswith(('.html', '.htm')):
            return 'html'
        elif url_lower.endswith('.txt'):
            return 'text'
        
        # Check content-type header
        ct_lower = content_type.lower()
        if 'pdf' in ct_lower:
            return 'pdf'
        elif 'csv' in ct_lower:
            return 'csv'
        elif 'excel' in ct_lower or 'spreadsheet' in ct_lower:
            return 'excel'
        elif 'json' in ct_lower:
            return 'json'
        elif 'image' in ct_lower:
            return 'image'
        elif 'html' in ct_lower:
            return 'html'
        elif 'text' in ct_lower:
            return 'text'
        
        # Check magic bytes
        if content[:4] == b'%PDF':
            return 'pdf'
        elif content[:2] == b'PK':  # ZIP-based formats (xlsx, docx, etc.)
            return 'excel'
        elif content[:8] == b'\x89PNG\r\n\x1a\n':
            return 'image'
        elif content[:2] in [b'\xff\xd8', b'\xff\xe0', b'\xff\xe1']:
            return 'image'
        
        # Try to decode as text
        try:
            text = content.decode('utf-8')
            if text.strip().startswith('{') or text.strip().startswith('['):
                return 'json'
            elif ',' in text and '\n' in text:
                return 'csv'
            elif '<html' in text.lower() or '<!doctype' in text.lower():
                return 'html'
            return 'text'
        except:
            return 'binary'
    
    @staticmethod
    def process_pdf(content: bytes) -> Dict[str, Any]:
        """Extract text and tables from PDF"""
        result = {
            'text': '',
            'pages': [],
            'tables': []
        }
        
        if HAS_PDFPLUMBER:
            try:
                with pdfplumber.open(io.BytesIO(content)) as pdf:
                    for i, page in enumerate(pdf.pages):
                        page_text = page.extract_text() or ''
                        result['pages'].append({
                            'page_number': i + 1,
                            'text': page_text
                        })
                        result['text'] += f"\n--- Page {i + 1} ---\n{page_text}"
                        
                        # Extract tables
                        tables = page.extract_tables()
                        for table in tables:
                            if table:
                                result['tables'].append({
                                    'page': i + 1,
                                    'data': table
                                })
                return result
            except Exception as e:
                print(f"pdfplumber error: {e}")
        
        if HAS_PYPDF2:
            try:
                reader = PyPDF2.PdfReader(io.BytesIO(content))
                for i, page in enumerate(reader.pages):
                    page_text = page.extract_text() or ''
                    result['pages'].append({
                        'page_number': i + 1,
                        'text': page_text
                    })
                    result['text'] += f"\n--- Page {i + 1} ---\n{page_text}"
                return result
            except Exception as e:
                print(f"PyPDF2 error: {e}")
        
        return result
    
    @staticmethod
    def process_csv(content: bytes, delimiter: str = ',') -> pd.DataFrame:
        """Parse CSV content into DataFrame"""
        try:
            # Try UTF-8 first
            text = content.decode('utf-8')
        except:
            # Fall back to latin-1
            text = content.decode('latin-1')
        
        # Auto-detect delimiter
        first_line = text.split('\n')[0]
        if '\t' in first_line and delimiter == ',':
            delimiter = '\t'
        elif ';' in first_line and ',' not in first_line:
            delimiter = ';'
        
        return pd.read_csv(io.StringIO(text), delimiter=delimiter)
    
    @staticmethod
    def process_excel(content: bytes, sheet_name: Union[str, int] = 0) -> pd.DataFrame:
        """Parse Excel content into DataFrame"""
        return pd.read_excel(io.BytesIO(content), sheet_name=sheet_name)
    
    @staticmethod
    def process_json(content: bytes) -> Any:
        """Parse JSON content"""
        try:
            text = content.decode('utf-8')
        except:
            text = content.decode('latin-1')
        return json.loads(text)
    
    @staticmethod
    def process_image(content: bytes) -> Dict[str, Any]:
        """Process image and return info + base64"""
        img = Image.open(io.BytesIO(content))
        
        # Get image format
        format_map = {'JPEG': 'jpeg', 'PNG': 'png', 'GIF': 'gif', 'WEBP': 'webp'}
        img_format = format_map.get(img.format, 'png')
        
        # Convert to base64
        buffered = io.BytesIO()
        img.save(buffered, format=img.format or 'PNG')
        base64_data = base64.b64encode(buffered.getvalue()).decode()
        
        return {
            'width': img.width,
            'height': img.height,
            'format': img_format,
            'mode': img.mode,
            'base64': base64_data,
            'data_uri': f"data:image/{img_format};base64,{base64_data}",
            'raw': content
        }
    
    @staticmethod
    def process_html(content: bytes) -> str:
        """Extract text from HTML"""
        try:
            text = content.decode('utf-8')
        except:
            text = content.decode('latin-1')
        
        # Simple HTML tag removal
        text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'<[^>]+>', ' ', text)
        text = re.sub(r'\s+', ' ', text)
        return text.strip()
    
    @staticmethod
    def dataframe_to_context(df: pd.DataFrame, max_rows: int = 100) -> str:
        """Convert DataFrame to string context for LLM"""
        info = f"Shape: {df.shape[0]} rows, {df.shape[1]} columns\n"
        info += f"Columns: {list(df.columns)}\n"
        info += f"Data types:\n{df.dtypes.to_string()}\n\n"
        
        if len(df) > max_rows:
            info += f"First {max_rows} rows:\n"
            info += df.head(max_rows).to_string()
        else:
            info += "Data:\n"
            info += df.to_string()
        
        return info
    
    @staticmethod
    def calculate_statistics(df: pd.DataFrame, column: str = None) -> Dict[str, Any]:
        """Calculate statistics for DataFrame or specific column"""
        if column:
            if column not in df.columns:
                return {"error": f"Column '{column}' not found"}
            
            col = df[column]
            if pd.api.types.is_numeric_dtype(col):
                return {
                    "column": column,
                    "count": int(col.count()),
                    "sum": float(col.sum()),
                    "mean": float(col.mean()),
                    "median": float(col.median()),
                    "min": float(col.min()),
                    "max": float(col.max()),
                    "std": float(col.std())
                }
            else:
                return {
                    "column": column,
                    "count": int(col.count()),
                    "unique": int(col.nunique()),
                    "top": str(col.mode().iloc[0]) if not col.mode().empty else None,
                    "freq": int(col.value_counts().iloc[0]) if not col.value_counts().empty else 0
                }
        else:
            return df.describe().to_dict()
    
    @staticmethod
    def filter_dataframe(df: pd.DataFrame, conditions: Dict[str, Any]) -> pd.DataFrame:
        """Filter DataFrame based on conditions"""
        result = df.copy()
        
        for column, condition in conditions.items():
            if column not in result.columns:
                continue
            
            if isinstance(condition, dict):
                for op, value in condition.items():
                    if op == 'eq' or op == '==':
                        result = result[result[column] == value]
                    elif op == 'ne' or op == '!=':
                        result = result[result[column] != value]
                    elif op == 'gt' or op == '>':
                        result = result[result[column] > value]
                    elif op == 'gte' or op == '>=':
                        result = result[result[column] >= value]
                    elif op == 'lt' or op == '<':
                        result = result[result[column] < value]
                    elif op == 'lte' or op == '<=':
                        result = result[result[column] <= value]
                    elif op == 'in':
                        result = result[result[column].isin(value)]
                    elif op == 'contains':
                        result = result[result[column].astype(str).str.contains(value, case=False)]
            else:
                result = result[result[column] == condition]
        
        return result
    
    @staticmethod
    def aggregate_dataframe(df: pd.DataFrame, group_by: List[str], agg_funcs: Dict[str, str]) -> pd.DataFrame:
        """Aggregate DataFrame"""
        return df.groupby(group_by).agg(agg_funcs).reset_index()
    
    @staticmethod
    def create_chart_base64(df: pd.DataFrame, chart_type: str, x: str, y: str, title: str = "") -> str:
        """Create a chart and return as base64"""
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        
        fig, ax = plt.subplots(figsize=(10, 6))
        
        if chart_type == 'bar':
            df.plot(kind='bar', x=x, y=y, ax=ax)
        elif chart_type == 'line':
            df.plot(kind='line', x=x, y=y, ax=ax)
        elif chart_type == 'scatter':
            df.plot(kind='scatter', x=x, y=y, ax=ax)
        elif chart_type == 'pie':
            df.set_index(x)[y].plot(kind='pie', ax=ax, autopct='%1.1f%%')
        elif chart_type == 'hist':
            df[y].plot(kind='hist', ax=ax)
        else:
            df.plot(x=x, y=y, ax=ax)
        
        if title:
            ax.set_title(title)
        
        plt.tight_layout()
        
        # Save to bytes
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=100, bbox_inches='tight')
        buf.seek(0)
        plt.close(fig)
        
        return base64.b64encode(buf.getvalue()).decode()


# Global processor instance
processor = DataProcessor()

