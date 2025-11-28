"""
Ryx AI - Web Scraper
Legal web scraping for learning and research
"""

from typing import Optional, Dict, List
from pathlib import Path
from urllib.parse import urlparse, urljoin
import requests
from bs4 import BeautifulSoup
import hashlib
import json
import time

# ===================================
# Web Scraper
# ===================================

class WebScraper:
    """Legal web scraping for learning and research"""
    
    def __init__(self):
        self.headers = {
            'User-Agent': 'Ryx-AI/1.0 (Educational; +https://github.com/ryx-ai)'
        }
        self.cache_dir = Path.home() / "ryx-ai" / "data" / "cache" / "scraped"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
    
    def scrape(self, url: str, extract_text: bool = True) -> Optional[Dict]:
        """
        Scrape webpage content
        
        Returns:
        {
            "url": str,
            "title": str,
            "text": str,
            "links": list,
            "metadata": dict
        }
        """
        print(f"\033[1;36m▸\033[0m Scraping: {url}")
        
        try:
            # Respect robots.txt (simple check)
            if not self._check_robots(url):
                print("\033[1;33m⚠\033[0m robots.txt disallows scraping")
                return None
            
            # Fetch page
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            
            # Parse HTML
            soup = BeautifulSoup(response.text, 'lxml')
            
            # Extract data
            data = {
                "url": url,
                "title": soup.title.string if soup.title else "No title",
                "text": self._extract_text(soup) if extract_text else "",
                "links": self._extract_links(soup, url),
                "metadata": self._extract_metadata(soup)
            }
            
            # Save to cache
            self._cache_result(url, data)
            
            # Display summary
            self._display_summary(data)
            
            return data
            
        except requests.exceptions.RequestException as e:
            print(f"\033[1;31m✗\033[0m Error fetching URL: {e}")
            return None
        except Exception as e:
            print(f"\033[1;31m✗\033[0m Error parsing content: {e}")
            return None
    
    def _check_robots(self, url: str) -> bool:
        """Simple robots.txt check"""
        parsed = urlparse(url)
        robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
        
        try:
            response = requests.get(robots_url, timeout=5)
            if response.status_code == 200:
                # Very basic check - just see if user-agent * is disallowed
                if "Disallow: /" in response.text:
                    return False
            return True
        except:
            # If can't fetch robots.txt, assume OK
            return True
    
    def _extract_text(self, soup: BeautifulSoup) -> str:
        """Extract main text content"""
        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.decompose()
        
        # Get text
        text = soup.get_text()
        
        # Clean up
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = ' '.join(chunk for chunk in chunks if chunk)
        
        return text[:5000]  # Limit to 5000 chars
    
    def _extract_links(self, soup: BeautifulSoup, base_url: str) -> List[str]:
        """Extract links from page"""
        links = []
        for link in soup.find_all('a', href=True):
            href = link['href']
            full_url = urljoin(base_url, href)
            links.append(full_url)
        
        return links[:50]  # Limit to 50 links
    
    def _extract_metadata(self, soup: BeautifulSoup) -> Dict:
        """Extract metadata (description, keywords, etc)"""
        metadata = {}
        
        # Description
        desc = soup.find('meta', attrs={'name': 'description'})
        if desc:
            metadata['description'] = desc.get('content', '')
        
        # Keywords
        keywords = soup.find('meta', attrs={'name': 'keywords'})
        if keywords:
            metadata['keywords'] = keywords.get('content', '')
        
        return metadata
    
    def _cache_result(self, url: str, data: Dict):
        """Cache scraped data"""
        import hashlib
        url_hash = hashlib.md5(url.encode()).hexdigest()
        cache_file = self.cache_dir / f"{url_hash}.json"
        
        with open(cache_file, 'w') as f:
            json.dump(data, f, indent=2)
    
    def _display_summary(self, data: Dict):
        """Display scraping summary"""
        print()
        print(f"\033[1;32m✓\033[0m \033[1m{data['title']}\033[0m")
        print()
        
        if data.get('metadata', {}).get('description'):
            print(f"\033[2m{data['metadata']['description'][:200]}...\033[0m")
            print()
        
        print(f"\033[1;36mText length:\033[0m {len(data['text'])} characters")
        print(f"\033[1;36mLinks found:\033[0m {len(data['links'])}")
        print()
        print(f"\033[2mCached to: {self.cache_dir}\033[0m")
        print()