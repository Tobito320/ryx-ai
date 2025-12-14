"""
Reader Mode - Firefox Feature

Extracts article content and displays in clean, readable format.
Removes ads, navigation, and distractions.
"""

from typing import Optional
import logging

log = logging.getLogger("ryxsurf.reader_mode")


class ReaderMode:
    """Manages reader mode for web pages"""
    
    def __init__(self):
        self.active = False
        self.original_html: Optional[str] = None
        
        # Reader mode JavaScript for content extraction
        self.extract_script = """
        (function() {
            // Readability.js-inspired content extraction
            
            function getArticleContent() {
                // Try common article selectors
                const selectors = [
                    'article',
                    '[role="main"]',
                    '.article-content',
                    '.post-content',
                    '.entry-content',
                    '#content',
                    'main'
                ];
                
                for (const selector of selectors) {
                    const elem = document.querySelector(selector);
                    if (elem && elem.textContent.length > 500) {
                        return elem;
                    }
                }
                
                // Fallback: find largest text block
                const allDivs = document.querySelectorAll('div, section, article');
                let bestElem = null;
                let maxScore = 0;
                
                for (const elem of allDivs) {
                    const text = elem.textContent || '';
                    const links = elem.querySelectorAll('a').length;
                    const paragraphs = elem.querySelectorAll('p').length;
                    
                    // Score: favor text and paragraphs, penalize links
                    const score = text.length + (paragraphs * 100) - (links * 50);
                    
                    if (score > maxScore) {
                        maxScore = score;
                        bestElem = elem;
                    }
                }
                
                return bestElem;
            }
            
            function extractMetadata() {
                return {
                    title: document.title,
                    author: document.querySelector('meta[name="author"]')?.content || '',
                    description: document.querySelector('meta[name="description"]')?.content || '',
                    publishDate: document.querySelector('meta[property="article:published_time"]')?.content || '',
                    siteName: document.querySelector('meta[property="og:site_name"]')?.content || '',
                };
            }
            
            function cleanContent(elem) {
                if (!elem) return '';
                
                // Clone to avoid modifying original
                const clone = elem.cloneNode(true);
                
                // Remove unwanted elements
                const unwanted = [
                    'script', 'style', 'iframe', 'object', 'embed',
                    'nav', 'header', 'footer', 'aside',
                    '.ad', '.ads', '.advertisement', '.social-share',
                    '.comments', '.related', '.sidebar'
                ];
                
                for (const selector of unwanted) {
                    const elems = clone.querySelectorAll(selector);
                    elems.forEach(e => e.remove());
                }
                
                // Clean attributes
                const allElems = clone.querySelectorAll('*');
                for (const el of allElems) {
                    // Keep only essential attributes
                    const attrs = Array.from(el.attributes);
                    for (const attr of attrs) {
                        if (!['href', 'src', 'alt', 'title'].includes(attr.name)) {
                            el.removeAttribute(attr.name);
                        }
                    }
                }
                
                return clone.innerHTML;
            }
            
            const article = getArticleContent();
            const metadata = extractMetadata();
            const content = cleanContent(article);
            
            return {
                metadata: metadata,
                content: content,
                success: content.length > 200
            };
        })();
        """
        
        # Reader mode styling
        self.reader_style = """
        <style>
            * {
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }
            
            body {
                font-family: 'Georgia', 'Times New Roman', serif;
                font-size: 18px;
                line-height: 1.8;
                color: #333;
                background: #f5f5f5;
                padding: 0;
                margin: 0;
            }
            
            .reader-container {
                max-width: 700px;
                margin: 0 auto;
                padding: 40px 20px;
                background: #fff;
                box-shadow: 0 0 60px rgba(0,0,0,0.1);
                min-height: 100vh;
            }
            
            .reader-header {
                margin-bottom: 40px;
                padding-bottom: 30px;
                border-bottom: 1px solid #e0e0e0;
            }
            
            .reader-title {
                font-size: 36px;
                font-weight: 700;
                line-height: 1.3;
                margin-bottom: 16px;
                color: #1a1a1a;
            }
            
            .reader-meta {
                font-size: 14px;
                color: #666;
                font-family: system-ui, sans-serif;
            }
            
            .reader-meta span {
                margin-right: 16px;
            }
            
            .reader-content {
                font-size: 18px;
                line-height: 1.8;
            }
            
            .reader-content p {
                margin-bottom: 1.5em;
            }
            
            .reader-content h1,
            .reader-content h2,
            .reader-content h3,
            .reader-content h4 {
                margin-top: 1.8em;
                margin-bottom: 0.6em;
                font-weight: 600;
                line-height: 1.4;
                color: #1a1a1a;
            }
            
            .reader-content h1 { font-size: 32px; }
            .reader-content h2 { font-size: 28px; }
            .reader-content h3 { font-size: 24px; }
            .reader-content h4 { font-size: 20px; }
            
            .reader-content img {
                max-width: 100%;
                height: auto;
                display: block;
                margin: 2em auto;
                border-radius: 4px;
            }
            
            .reader-content a {
                color: #0066cc;
                text-decoration: none;
                border-bottom: 1px solid #0066cc;
            }
            
            .reader-content a:hover {
                background: #f0f7ff;
            }
            
            .reader-content blockquote {
                margin: 1.5em 0;
                padding-left: 20px;
                border-left: 4px solid #e0e0e0;
                font-style: italic;
                color: #555;
            }
            
            .reader-content pre,
            .reader-content code {
                font-family: 'Fira Code', 'Courier New', monospace;
                background: #f8f8f8;
                border-radius: 3px;
            }
            
            .reader-content code {
                padding: 2px 6px;
                font-size: 0.9em;
            }
            
            .reader-content pre {
                padding: 16px;
                overflow-x: auto;
                margin: 1.5em 0;
            }
            
            .reader-content ul,
            .reader-content ol {
                margin: 1em 0 1em 2em;
            }
            
            .reader-content li {
                margin-bottom: 0.5em;
            }
            
            .reader-toolbar {
                position: fixed;
                top: 20px;
                right: 20px;
                background: #fff;
                border-radius: 8px;
                padding: 8px;
                box-shadow: 0 2px 12px rgba(0,0,0,0.15);
                display: flex;
                gap: 4px;
            }
            
            .reader-toolbar button {
                background: transparent;
                border: none;
                padding: 8px 12px;
                cursor: pointer;
                border-radius: 4px;
                font-size: 14px;
                color: #666;
            }
            
            .reader-toolbar button:hover {
                background: #f0f0f0;
                color: #1a1a1a;
            }
            
            /* Dark mode */
            @media (prefers-color-scheme: dark) {
                body {
                    background: #1a1a1a;
                    color: #e0e0e0;
                }
                
                .reader-container {
                    background: #2a2a2a;
                    box-shadow: 0 0 60px rgba(0,0,0,0.5);
                }
                
                .reader-title,
                .reader-content h1,
                .reader-content h2,
                .reader-content h3,
                .reader-content h4 {
                    color: #f0f0f0;
                }
                
                .reader-content a {
                    color: #6699ff;
                    border-bottom-color: #6699ff;
                }
                
                .reader-content a:hover {
                    background: #2a3a4a;
                }
                
                .reader-content blockquote {
                    border-left-color: #444;
                    color: #bbb;
                }
                
                .reader-content pre,
                .reader-content code {
                    background: #1a1a1a;
                    color: #e0e0e0;
                }
                
                .reader-toolbar {
                    background: #2a2a2a;
                    border: 1px solid #444;
                }
                
                .reader-toolbar button {
                    color: #bbb;
                }
                
                .reader-toolbar button:hover {
                    background: #3a3a3a;
                    color: #f0f0f0;
                }
            }
        </style>
        """
    
    def format_reader_page(self, data: dict) -> str:
        """Format extracted content as reader mode page"""
        meta = data.get('metadata', {})
        content = data.get('content', '')
        
        # Build metadata string
        meta_parts = []
        if meta.get('author'):
            meta_parts.append(f"<span>By {meta['author']}</span>")
        if meta.get('publishDate'):
            meta_parts.append(f"<span>{meta['publishDate']}</span>")
        if meta.get('siteName'):
            meta_parts.append(f"<span>{meta['siteName']}</span>")
        
        meta_html = ' '.join(meta_parts)
        
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>{meta.get('title', 'Reader Mode')}</title>
            {self.reader_style}
        </head>
        <body>
            <div class="reader-toolbar">
                <button onclick="window.history.back()" title="Exit Reader Mode">✕ Exit</button>
                <button onclick="document.body.style.fontSize = (parseInt(getComputedStyle(document.body).fontSize) + 2) + 'px'" title="Increase font size">A+</button>
                <button onclick="document.body.style.fontSize = (parseInt(getComputedStyle(document.body).fontSize) - 2) + 'px'" title="Decrease font size">A-</button>
                <button onclick="window.print()" title="Print">🖨</button>
            </div>
            <div class="reader-container">
                <div class="reader-header">
                    <h1 class="reader-title">{meta.get('title', 'Untitled')}</h1>
                    <div class="reader-meta">{meta_html}</div>
                </div>
                <div class="reader-content">
                    {content}
                </div>
            </div>
        </body>
        </html>
        """
    
    def is_available_for_page(self, url: str) -> bool:
        """Check if reader mode is available for this page"""
        # Skip for non-article pages
        skip_patterns = [
            'youtube.com', 'github.com', 'twitter.com', 'x.com',
            'reddit.com', 'facebook.com', 'instagram.com',
            'google.com', 'duckduckgo.com', 'bing.com'
        ]
        
        for pattern in skip_patterns:
            if pattern in url:
                return False
        
        # Available for article-like pages
        return url.startswith('http')
