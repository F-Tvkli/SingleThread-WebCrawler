import os
import logging
import urllib.robotparser
import requests
from collections import deque
from urllib.parse import urlparse

class URLFrontier:
    """
    Advanced Queue Management System with Strict Polite Scheduling.
    Implements a robust HTTP fetching mechanism for robots.txt to bypass native socket timeouts.
    Enforces a strict fail-safe: if the file cannot be reached due to network failure, 
    the crawler assumes a Disallow-All state to prevent bandwidth waste.
    """
    def __init__(self, base_domain: str, user_agent: str, max_memory_size: int = 5000, max_depth: int = 10):
        self.base_domain = base_domain
        self.user_agent = user_agent
        self.max_depth = max_depth
        self.queue = deque()
        self.visited = set()
        self.discovered_count = 0
        self.logger = logging.getLogger(__name__)
        
        self.max_memory_size = max_memory_size
        self.spill_file = "queue_spill.txt"
        
        if os.path.exists(self.spill_file):
            os.remove(self.spill_file)
            
        self.rp = urllib.robotparser.RobotFileParser()
        robots_url = f"https://{self.base_domain}/robots.txt"
        self.rp.set_url(robots_url)
        
        # Robust robots.txt initialization via requests
        self._initialize_robots_txt(robots_url)

    def _initialize_robots_txt(self, url: str):
        try:
            self.logger.info(f"Fetching robots.txt from {url} ...")
            headers = {'User-Agent': self.user_agent}
            # 10-second strict timeout for the initial policy fetch
            resp = requests.get(url, headers=headers, timeout=10)
            
            if resp.status_code == 200:
                # Parse the text manually and feed it to the standard robotparser
                lines = resp.text.splitlines()
                self.rp.parse(lines)
                self.logger.info(f"Successfully loaded and enforced robots.txt for {self.base_domain}")
            elif resp.status_code in (401, 403):
                self.logger.warning("Access to robots.txt is forbidden (403). Enforcing strict Deny-All policy.")
                self.rp.disallow_all = True
            else:
                self.logger.info(f"No robots.txt found (HTTP {resp.status_code}). Assuming Allow-All.")
                self.rp.allow_all = True
                
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Network failure while fetching robots.txt: {e}")
            self.logger.warning("Strict politeness enforced: Halting access to domain to prevent blind crawling.")
            self.rp.disallow_all = True

    def add_url(self, url: str, depth: int) -> bool:
        if depth > self.max_depth:
            return False
            
        # Standard politeness evaluation against the loaded ruleset
        if not self.rp.can_fetch(self.user_agent, url):
            return False
            
        self.discovered_count += 1
        
        if url in self.visited:
            return False
            
        domain = urlparse(url).netloc
        if self.base_domain in domain:
            self.visited.add(url)
            self.queue.append((url, depth))
            
            if len(self.queue) > self.max_memory_size:
                self._spill_to_disk()
            return True
        return False

    def get_next_url(self) -> tuple[str, int] | None:
        if not self.queue:
            self._load_from_disk()
            
        if self.queue:
            return self.queue.popleft()
        return None

    def _spill_to_disk(self):
        spill_count = len(self.queue) // 2
        self.logger.info(f"RAM optimization: Spilling {spill_count} URLs to disk storage.")
        queue_list = list(self.queue)
        keep_in_mem = queue_list[:-spill_count]
        spill_to_disk = queue_list[-spill_count:]
        self.queue = deque(keep_in_mem)
        with open(self.spill_file, "a", encoding="utf-8") as f:
            for url, depth in spill_to_disk:
                f.write(f"{url},{depth}\n")

    def _load_from_disk(self):
        if not os.path.exists(self.spill_file):
            return
        with open(self.spill_file, "r", encoding="utf-8") as f:
            lines = f.readlines()
        load_count = min(len(lines), self.max_memory_size)
        for i in range(load_count):
            parts = lines[i].strip().split(',')
            if len(parts) == 2:
                self.queue.append((parts[0], int(parts[1])))
        remaining_lines = lines[load_count:]
        if remaining_lines:
            with open(self.spill_file, "w", encoding="utf-8") as f:
                f.writelines(remaining_lines)
        else:
            os.remove(self.spill_file)