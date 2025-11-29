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

        # NEW: RAG scrape directory for human-readable content
        self.scrape_dir = Path.home() / "ryx-ai" / "data" / "scrape"
        self.scrape_dir.mkdir(parents=True, exist_ok=True)
    
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
            
            # Save to cache (JSON format)
            self._cache_result(url, data)

            # NEW: Save to scrape folder (human-readable TXT format)
            self._save_to_scrape(url, data)

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
        """Improved robots.txt check"""
        parsed = urlparse(url)
        robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
        path = parsed.path

        try:
            response = requests.get(robots_url, timeout=5)
            if response.status_code == 200:
                # Check if this specific path is disallowed
                for line in response.text.split('\n'):
                    line = line.strip()
                    if line.startswith('Disallow:'):
                        disallowed_path = line.split(':', 1)[1].strip()
                        if disallowed_path == '/':
                            # Everything is disallowed
                            return False
                        # Check if our path starts with disallowed path
                        if path.startswith(disallowed_path):
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

    def _save_to_scrape(self, url: str, data: Dict):
        """
        Save scraped content to scrape folder in human-readable format
        Automatically categorizes into subdirectories based on URL
        """
        from datetime import datetime

        # Determine category from URL
        parsed = urlparse(url)
        domain = parsed.netloc.lower()

        if 'arch' in domain and 'wiki' in domain:
            category = 'arch-wiki'
        elif 'documentation' in url.lower() or 'docs' in domain:
            category = 'documentation'
        elif 'tutorial' in url.lower() or 'guide' in url.lower():
            category = 'tutorials'
        else:
            category = 'documentation'  # default

        # Create category directory
        category_dir = self.scrape_dir / category
        category_dir.mkdir(parents=True, exist_ok=True)

        # Generate filename from URL (sanitized)
        url_hash = hashlib.md5(url.encode()).hexdigest()[:8]
        title_clean = "".join(c if c.isalnum() or c in (' ', '-', '_') else '_'
                             for c in data['title'][:50])
        filename = f"{title_clean}_{url_hash}.txt"

        # Create human-readable content
        content = f"""
╔════════════════════════════════════════════════════════════════════╗
║  SCRAPED DOCUMENTATION                                             ║
╚════════════════════════════════════════════════════════════════════╝

Title: {data['title']}
URL: {data['url']}
Scraped: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Category: {category}

{'─' * 70}
DESCRIPTION
{'─' * 70}

{data.get('metadata', {}).get('description', 'No description available')}

{'─' * 70}
CONTENT
{'─' * 70}

{data['text']}

{'─' * 70}
LINKS ({len(data['links'])} total)
{'─' * 70}

{chr(10).join('  • ' + link for link in data['links'][:20])}

{'─' * 70}
END OF DOCUMENT
{'─' * 70}
"""

        # Save to file
        file_path = category_dir / filename
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content.strip())

        print(f"\033[1;32m✓\033[0m Saved to: {file_path}")

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