"""
Browser automation using Playwright for JavaScript-rendered pages
"""
import asyncio
from playwright.async_api import async_playwright, Browser, Page, BrowserContext
from typing import Optional, Tuple, List
import base64
import re
from config import BROWSER_TIMEOUT

class BrowserHandler:
    def __init__(self):
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
    
    async def start(self):
        """Initialize the browser"""
        if not self.playwright:
            self.playwright = await async_playwright().start()
            self.browser = await self.playwright.chromium.launch(
                headless=True,
                args=[
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-gpu'
                ]
            )
            self.context = await self.browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            )
    
    async def stop(self):
        """Close the browser"""
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
        self.playwright = None
        self.browser = None
        self.context = None
    
    async def get_page_content(self, url: str) -> Tuple[str, str]:
        """
        Navigate to URL and get rendered HTML content
        Returns: (text_content, html_content)
        """
        await self.start()
        page = await self.context.new_page()
        
        try:
            await page.goto(url, wait_until='networkidle', timeout=BROWSER_TIMEOUT)
            await page.wait_for_timeout(2000)  # Wait for JS to execute
            
            # Get the rendered HTML
            html_content = await page.content()
            
            # Get text content
            text_content = await page.evaluate('''() => {
                return document.body.innerText || document.body.textContent;
            }''')
            
            return text_content.strip(), html_content
        finally:
            await page.close()
    
    async def get_page_with_screenshot(self, url: str) -> Tuple[str, str, bytes]:
        """
        Get page content and screenshot
        Returns: (text_content, html_content, screenshot_bytes)
        """
        await self.start()
        page = await self.context.new_page()
        
        try:
            await page.goto(url, wait_until='networkidle', timeout=BROWSER_TIMEOUT)
            await page.wait_for_timeout(2000)
            
            html_content = await page.content()
            text_content = await page.evaluate('''() => {
                return document.body.innerText || document.body.textContent;
            }''')
            screenshot = await page.screenshot(full_page=True)
            
            return text_content.strip(), html_content, screenshot
        finally:
            await page.close()
    
    async def download_file(self, url: str) -> Tuple[bytes, str]:
        """
        Download a file from URL
        Returns: (file_bytes, content_type)
        """
        await self.start()
        page = await self.context.new_page()
        
        try:
            response = await page.goto(url, timeout=BROWSER_TIMEOUT)
            content_type = response.headers.get('content-type', 'application/octet-stream')
            content = await response.body()
            return content, content_type
        finally:
            await page.close()
    
    async def extract_links(self, url: str) -> List[dict]:
        """Extract all links from a page"""
        await self.start()
        page = await self.context.new_page()
        
        try:
            await page.goto(url, wait_until='networkidle', timeout=BROWSER_TIMEOUT)
            await page.wait_for_timeout(1000)
            
            links = await page.evaluate('''() => {
                const anchors = document.querySelectorAll('a[href]');
                return Array.from(anchors).map(a => ({
                    href: a.href,
                    text: a.innerText.trim()
                }));
            }''')
            
            return links
        finally:
            await page.close()
    
    async def execute_script(self, url: str, script: str) -> any:
        """Execute JavaScript on a page and return result"""
        await self.start()
        page = await self.context.new_page()
        
        try:
            await page.goto(url, wait_until='networkidle', timeout=BROWSER_TIMEOUT)
            await page.wait_for_timeout(1000)
            result = await page.evaluate(script)
            return result
        finally:
            await page.close()
    
    async def fill_form_and_submit(self, url: str, form_data: dict, submit_selector: str = None) -> str:
        """Fill a form and submit it"""
        await self.start()
        page = await self.context.new_page()
        
        try:
            await page.goto(url, wait_until='networkidle', timeout=BROWSER_TIMEOUT)
            
            for selector, value in form_data.items():
                await page.fill(selector, value)
            
            if submit_selector:
                await page.click(submit_selector)
                await page.wait_for_load_state('networkidle')
            
            return await page.content()
        finally:
            await page.close()
    
    async def get_table_data(self, url: str) -> List[List[str]]:
        """Extract table data from a page"""
        await self.start()
        page = await self.context.new_page()
        
        try:
            await page.goto(url, wait_until='networkidle', timeout=BROWSER_TIMEOUT)
            await page.wait_for_timeout(1000)
            
            tables = await page.evaluate('''() => {
                const tables = document.querySelectorAll('table');
                return Array.from(tables).map(table => {
                    const rows = table.querySelectorAll('tr');
                    return Array.from(rows).map(row => {
                        const cells = row.querySelectorAll('td, th');
                        return Array.from(cells).map(cell => cell.innerText.trim());
                    });
                });
            }''')
            
            return tables
        finally:
            await page.close()


# Singleton instance
_browser_handler = None

async def get_browser() -> BrowserHandler:
    global _browser_handler
    if _browser_handler is None:
        _browser_handler = BrowserHandler()
    return _browser_handler

async def close_browser():
    global _browser_handler
    if _browser_handler:
        await _browser_handler.stop()
        _browser_handler = None

