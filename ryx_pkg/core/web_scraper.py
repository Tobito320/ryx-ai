# -*- coding: utf-8 -*-
"""
Web Scraper - Web-Inhalte für Ryx Context abrufen
Inspiriert von Aider's scrape.py
"""

import asyncio
import re
from dataclasses import dataclass
from typing import Optional, List
from pathlib import Path
import logging
import tempfile

logger = logging.getLogger(__name__)


@dataclass
class ScrapedContent:
    """Ergebnis eines Web-Scrapes"""
    url: str
    title: Optional[str] = None
    content: str = ""  # Markdown/Text content
    raw_html: Optional[str] = None
    links: List[str] = None
    success: bool = True
    error: Optional[str] = None
    
    def __post_init__(self):
        if self.links is None:
            self.links = []


class WebScraper:
    """
    Web Scraper für Ryx
    
    Unterstützt:
    - Playwright (beste Qualität, JavaScript-Support)
    - requests + BeautifulSoup (Fallback, schneller)
    - HTML zu Markdown Konvertierung
    
    Usage:
        scraper = WebScraper()
        content = await scraper.scrape("https://example.com")
        print(content.content)
    """
    
    def __init__(self, user_agent: str = "RyxAI/1.0"):
        self.user_agent = user_agent
        self._playwright_available: Optional[bool] = None
        
    async def scrape(
        self,
        url: str,
        use_playwright: bool = False,
        extract_links: bool = False
    ) -> ScrapedContent:
        """
        Scrape eine URL
        
        Args:
            url: URL zum Scrapen
            use_playwright: Playwright für JavaScript-Seiten nutzen
            extract_links: Links aus der Seite extrahieren
            
        Returns:
            ScrapedContent mit Markdown-Content
        """
        try:
            if use_playwright and await self._check_playwright():
                return await self._scrape_playwright(url, extract_links)
            else:
                return await self._scrape_requests(url, extract_links)
        except Exception as e:
            logger.error(f"Scrape error for {url}: {e}")
            return ScrapedContent(
                url=url,
                success=False,
                error=str(e)
            )
            
    async def _check_playwright(self) -> bool:
        """Prüfe ob Playwright verfügbar ist"""
        if self._playwright_available is not None:
            return self._playwright_available
            
        try:
            from playwright.async_api import async_playwright
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                await browser.close()
            self._playwright_available = True
        except Exception:
            self._playwright_available = False
            
        return self._playwright_available
        
    async def _scrape_playwright(self, url: str, extract_links: bool) -> ScrapedContent:
        """Scrape mit Playwright"""
        from playwright.async_api import async_playwright
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page(user_agent=self.user_agent)
            
            try:
                await page.goto(url, wait_until="networkidle", timeout=30000)
                
                # Warte kurz für dynamischen Content
                await asyncio.sleep(1)
                
                title = await page.title()
                html = await page.content()
                
                links = []
                if extract_links:
                    link_elements = await page.query_selector_all("a[href]")
                    for elem in link_elements:
                        href = await elem.get_attribute("href")
                        if href and href.startswith("http"):
                            links.append(href)
                            
                content = await self._html_to_markdown(html)
                
                return ScrapedContent(
                    url=url,
                    title=title,
                    content=content,
                    raw_html=html,
                    links=links[:50]  # Limitiere Links
                )
                
            finally:
                await browser.close()
                
    async def _scrape_requests(self, url: str, extract_links: bool) -> ScrapedContent:
        """Scrape mit requests + BeautifulSoup"""
        try:
            import requests
            from bs4 import BeautifulSoup
        except ImportError:
            logger.error("requests/beautifulsoup4 not installed")
            return ScrapedContent(url=url, success=False, error="Dependencies missing")
            
        headers = {"User-Agent": self.user_agent}
        
        response = await asyncio.to_thread(
            lambda: requests.get(url, headers=headers, timeout=30)
        )
        response.raise_for_status()
        
        html = response.text
        soup = BeautifulSoup(html, "html.parser")
        
        # Titel extrahieren
        title = soup.title.string if soup.title else None
        
        # Links extrahieren
        links = []
        if extract_links:
            for a in soup.find_all("a", href=True):
                href = a["href"]
                if href.startswith("http"):
                    links.append(href)
                    
        # HTML zu Markdown
        content = await self._html_to_markdown(html)
        
        return ScrapedContent(
            url=url,
            title=title,
            content=content,
            raw_html=html,
            links=links[:50]
        )
        
    async def _html_to_markdown(self, html: str) -> str:
        """Konvertiere HTML zu Markdown"""
        # Versuche pypandoc
        try:
            import pypandoc
            return pypandoc.convert_text(html, "markdown", format="html")
        except ImportError:
            pass
        except Exception as e:
            logger.debug(f"pypandoc error: {e}")
            
        # Fallback: html2text
        try:
            import html2text
            h = html2text.HTML2Text()
            h.ignore_links = False
            h.ignore_images = True
            h.body_width = 0
            return h.handle(html)
        except ImportError:
            pass
            
        # Letzter Fallback: BeautifulSoup get_text
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, "html.parser")
            
            # Entferne Script/Style
            for tag in soup(["script", "style", "nav", "footer", "header"]):
                tag.decompose()
                
            return soup.get_text(separator="\n", strip=True)
        except ImportError:
            pass
            
        # Ganz simpler Fallback
        return self._strip_html_simple(html)
        
    def _strip_html_simple(self, html: str) -> str:
        """Einfache HTML-Tag-Entfernung"""
        # Entferne Script/Style
        html = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
        html = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.DOTALL | re.IGNORECASE)
        
        # Entferne Tags
        html = re.sub(r'<[^>]+>', ' ', html)
        
        # Bereinige Whitespace
        html = re.sub(r'\s+', ' ', html)
        html = re.sub(r'\n\s*\n', '\n\n', html)
        
        return html.strip()
        
    async def scrape_multiple(
        self,
        urls: List[str],
        max_concurrent: int = 5
    ) -> List[ScrapedContent]:
        """Scrape mehrere URLs parallel"""
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def scrape_with_limit(url: str) -> ScrapedContent:
            async with semaphore:
                return await self.scrape(url)
                
        tasks = [scrape_with_limit(url) for url in urls]
        return await asyncio.gather(*tasks)
        
    async def extract_code_blocks(self, content: str) -> List[dict]:
        """Extrahiere Code-Blöcke aus Markdown"""
        pattern = r'```(\w+)?\n(.*?)```'
        matches = re.findall(pattern, content, re.DOTALL)
        
        return [
            {"language": lang or "text", "code": code.strip()}
            for lang, code in matches
        ]
