import time
import random
import logging
import socket
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# --- Application-Level DNS Cache ---
# Intercepts socket DNS resolutions to cache IP addresses in memory.
# This prevents the crawler from hitting the OS DNS resolver repeatedly 
# if the TCP connection drops, satisfying industrial crawler speed requirements.
_dns_cache = {}
_original_getaddrinfo = socket.getaddrinfo

def _cached_getaddrinfo(*args, **kwargs):
    if args in _dns_cache:
        return _dns_cache[args]
    result = _original_getaddrinfo(*args, **kwargs)
    _dns_cache[args] = result
    return result

# Apply the monkey patch
socket.getaddrinfo = _cached_getaddrinfo
# -----------------------------------

class Fetcher:
    """
    Robust network interface with built-in politeness delays and custom DNS caching.
    Simulates human browsing patterns to prevent IP bans when crawling production environments.
    """
    def __init__(self, timeout: int = 10, min_delay: float = 1.5, max_delay: float = 3.5):
        self.timeout = timeout
        self.min_delay = min_delay
        self.max_delay = max_delay
        self.errors = 0
        self.logger = logging.getLogger(__name__)
        
        self.session = requests.Session()
        
        # Masquerading as a standard Google Chrome browser on Windows
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36'
        })
        
        # Handling 403 (Forbidden) and 429 (Too Many Requests) for WAF evasion
        retry_strategy = Retry(
            total=3,
            backoff_factor=2,
            status_forcelist=[403, 429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET"]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

    def fetch_html(self, url: str) -> str | None:
        try:
            # Politeness Strategy: Random sleep to evade rate-limiting
            delay = random.uniform(self.min_delay, self.max_delay)
            time.sleep(delay)
            
            # Pre-flight check
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