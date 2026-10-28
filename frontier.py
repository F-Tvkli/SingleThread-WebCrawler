import os
import logging
from collections import deque
from urllib.parse import urlparse

class URLFrontier:
    """
    Hybrid Memory/Disk Queue system.
    I designed this to ensure the crawler never crashes my machine due to out-of-memory
    errors when the discovered URLs grow exponentially.
    """
    def __init__(self, base_domain: str, max_memory_size: int = 5000, max_depth: int = 5):
        self.base_domain = base_domain
        self.max_depth = max_depth
        self.queue = deque()
        self.visited = set()
        self.discovered_count = 0
        self.logger = logging.getLogger(__name__)
        
        self.max_memory_size = max_memory_size
        self.spill_file = "queue_spill.txt"
        
        if os.path.exists(self.spill_file):
            os.remove(self.spill_file)

    def add_url(self, url: str, depth: int) -> bool:
        if depth > self.max_depth:
            return False
            
        self.discovered_count += 1
        
        if url in self.visited:
            return False
            
        domain = urlparse(url).netloc
        if self.base_domain in domain:
            self.visited.add(url)
            self.queue.append((url, depth))
            
            # Flush data to disk when RAM threshold is reached
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