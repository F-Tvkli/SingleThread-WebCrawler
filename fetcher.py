import logging
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

class Fetcher:
    """
    Robust network interface. 
    I added connection pooling and strict timeouts to prevent the single thread 
    from hanging indefinitely if a target server drops the connection.
    """
    def __init__(self, timeout: int = 5):
        self.timeout = timeout
        self.errors = 0
        self.logger = logging.getLogger(__name__)
        
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (MyPersonalCrawlerBot/1.0)'
        })
        
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
        try:
            # Send HEAD first to verify content type, saving massive bandwidth
            head_resp = self.session.head(url, timeout=self.timeout, allow_redirects=True)
            content_type = head_resp.headers.get('Content-Type', '').lower()
            
            if 'text/html' not in content_type:
                return None

            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            return response.text
            
        except requests.exceptions.Timeout:
            self.errors += 1
            self.logger.warning(f"Timeout constraint breached for {url}. Dropping node.")
            return None
        except requests.exceptions.RequestException as e:
            self.errors += 1
            self.logger.warning(f"Network drop on {url}: {e}")
            return None