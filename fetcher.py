import logging
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

class Fetcher:
    """
    Handles HTTP communications with connection pooling and robust retry logic.
    Optimized to reduce latency in single-threaded crawling architectures.
    """
    def __init__(self, timeout: int = 5):
        self.timeout = timeout
        self.errors = 0
        self.logger = logging.getLogger(__name__)
        
        # Initialize a Session object for TCP connection reuse
        self.session = requests.Session()
        
        # Set a standard User-Agent to prevent basic bot-blocking by web servers
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
        # Configure retry strategy for transient network failures
        # Backoff factor 1 means it will sleep for [0, 2, 4] seconds between retries
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET"]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

    def fetch_html(self, url: str) -> str | None:
        """
        Fetches HTML content. Skips non-HTML files using an initial HEAD request.
        """
        try:
            # Pre-flight check to verify Content-Type before downloading the full body
            head_resp = self.session.head(url, timeout=self.timeout, allow_redirects=True)
            content_type = head_resp.headers.get('Content-Type', '').lower()
            
            # Ensure we only fetch HTML pages, ignoring PDFs, images, or media files
            if 'text/html' not in content_type:
                self.logger.debug(f"Skipping non-HTML content at {url}")
                return None

            # Fetch the actual HTML document
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            return response.text
            
        except requests.exceptions.RequestException as e:
            # Catching timeouts, connection errors, and invalid HTTP responses
            self.errors += 1
            self.logger.warning(f"Failed to fetch {url}: {e}")
            return None