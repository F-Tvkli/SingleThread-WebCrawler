import logging
from typing import Set
from urllib.parse import urljoin, urldefrag
from bs4 import BeautifulSoup

class Parser:
    """
    Extracts and normalizes absolute URLs from raw HTML content.
    Utilizes the C-based lxml engine for maximum single-threaded performance.
    """
    logger = logging.getLogger(__name__)

    @staticmethod
    def extract_links(html_content: str, current_url: str) -> Set[str]:
        """
        Parses the HTML DOM structure, finds all anchor tags, and yields a set of clean URLs.
        """
        clean_urls = set()
        
        try:
            # Parse the HTML document using lxml
            soup = BeautifulSoup(html_content, 'lxml')
            
            # Iterate over all <a> tags that have an 'href' attribute
            for tag in soup.find_all('a', href=True):
                raw_url = tag['href'].strip()
                
                # Ignore empty links or JavaScript triggers
                if not raw_url or raw_url.startswith(('javascript:', 'mailto:', 'tel:')):
                    continue
                
                # Convert relative URLs (e.g., /about) to absolute URLs (e.g., https://domain.com/about)
                absolute_url = urljoin(current_url, raw_url)
                
                # Remove URL fragments (e.g., #section1) to prevent logical duplicates
                normalized_url, _ = urldefrag(absolute_url)
                
                clean_urls.add(normalized_url)
                
        except Exception as e:
            Parser.logger.error(f"Failed to parse HTML for {current_url}: {e}")
            
        # Return a set to remove duplicate links found on the same page
        return clean_urls