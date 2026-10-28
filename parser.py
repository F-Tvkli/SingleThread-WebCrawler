import logging
from typing import Set
from urllib.parse import urljoin, urldefrag, urlparse, urlunparse
from bs4 import BeautifulSoup, SoupStrainer

class Parser:
    """
    High-performance parsing engine. 
    I built this using SoupStrainer to prevent memory leaks during massive crawls. 
    Instead of loading the entire HTML tree into RAM, it only parses anchor tags.
    """
    logger = logging.getLogger(__name__)

    @staticmethod
    def normalize_url(url: str) -> str:
        """
        Standardizes URLs so my uniqueness checker doesn't get bloated 
        with logically identical links that look slightly different.
        """
        url, _ = urldefrag(url)
        parsed = urlparse(url)
        
        netloc = parsed.netloc.lower()
        if netloc.startswith('www.'):
            netloc = netloc[4:]
            
        path = parsed.path
        if path.endswith('/') and len(path) > 1:
            path = path[:-1]
        
        if path.endswith('/index.html') or path.endswith('/index.htm'):
            path = path.rsplit('/', 1)[0]
            if not path:
                path = '/'
                
        return urlunparse((parsed.scheme.lower(), netloc, path, parsed.params, parsed.query, ''))

    @staticmethod
    def extract_links(html_content: str, current_url: str) -> Set[str]:
        clean_urls = set()
        try:
            # Memory Optimization: Only parse <a> tags with an href attribute
            # This drastically reduces RAM usage and CPU parsing time
            only_a_tags = SoupStrainer('a', href=True)
            soup = BeautifulSoup(html_content, 'html.parser', parse_only=only_a_tags)
            
            for tag in soup:
                raw_url = tag['href'].strip()
                
                if not raw_url or raw_url.startswith(('javascript:', 'mailto:', 'tel:')):
                    continue
                
                absolute_url = urljoin(current_url, raw_url)
                canonical_url = Parser.normalize_url(absolute_url)
                
                if canonical_url:
                    clean_urls.add(canonical_url)
                    
        except Exception as e:
            Parser.logger.error(f"DOM Parsing failed for {current_url}: {e}")
            
        return clean_urls