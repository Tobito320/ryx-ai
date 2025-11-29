# Extract WebBrowser class from ryx_tools.py

import requests
from bs4 import BeautifulSoup
from tools.scraper import WebScraper

# ===================================
# Web Browser
# ===================================

class WebBrowser:
    """Search and browse web content"""
    
    def __init__(self):
        self.scraper = WebScraper()
    
    def search(self, query: str, num_results: int = 5):
        """
        Search web and display results
        
        Uses DuckDuckGo (privacy-friendly)
        """
        print(f"\033[1;36m▸\033[0m Searching for: {query}")
        print()
        
        # Build search URL
        search_url = f"https://html.duckduckgo.com/html/?q={query}"
        
        try:
            response = requests.get(search_url, headers=self.scraper.headers, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'lxml')
            
            # Extract results
            results = []
            for result in soup.find_all('div', class_='result'):
                title_elem = result.find('a', class_='result__a')
                snippet_elem = result.find('a', class_='result__snippet')
                
                if title_elem:
                    url = title_elem['href']
                    # Fix relative URLs
                    if url.startswith('//'):
                        url = 'https:' + url
                    results.append({
                        'title': title_elem.get_text(strip=True),
                        'url': url,
                        'snippet': snippet_elem.get_text(strip=True) if snippet_elem else ""
                    })
            
            # Display results
            for i, result in enumerate(results[:num_results], 1):
                print(f"\033[1;33m[{i}]\033[0m \033[1m{result['title']}\033[0m")
                print(f"    {result['url']}")
                if result['snippet']:
                    print(f"    \033[2m{result['snippet'][:150]}...\033[0m")
                print()
            
            # Offer to scrape
            print("\033[1;36mScrape a result?\033[0m")
            choice = input("Enter number [1-{}] or 'n' to skip: ".format(num_results)).strip()
            
            if choice.isdigit() and 1 <= int(choice) <= len(results):
                idx = int(choice) - 1
                self.scraper.scrape(results[idx]['url'])
            
        except Exception as e:
            print(f"\033[1;31m✗\033[0m Search error: {e}")