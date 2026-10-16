import os
import logging
from collections import deque
from urllib.parse import urlparse

class URLFrontier:
    """
    Hybrid Memory/Disk URL Frontier Architecture.
    Manages BFS crawling queue and uses disk spillage to prevent RAM overflow.
    """
    def __init__(self, base_domain: str, max_memory_size: int = 5000):
        self.base_domain = base_domain
        self.queue = deque()
        self.visited = set()
        self.discovered_count = 0
        self.logger = logging.getLogger(__name__)
        
        # Disk Spillage Configurations
        self.max_memory_size = max_memory_size
        self.spill_file = "queue_spill.txt"
        
        # Remove previous session spill files if they exist
        if os.path.exists(self.spill_file):
            os.remove(self.spill_file)

    def add_url(self, url: str) -> bool:
        """Validates, deduplicates, and enqueues. Spills to disk if RAM is full."""
        self.discovered_count += 1
        
        # UChecker logic: O(1) deduplication check
        if url in self.visited:
            return False
            
        domain = urlparse(url).netloc
        # Ensure the URL belongs to the target domain or its subdomains
        if self.base_domain in domain:
            self.visited.add(url)
            self.queue.append(url)
            
            # Trigger Disk Spillage if RAM limit exceeded
            if len(self.queue) > self.max_memory_size:
                self._spill_to_disk()
            return True
            
        return False

    def get_next_url(self) -> str | None:
        """Retrieves the next URL for the Fetcher. Reloads from disk if needed."""
        # If memory queue is empty, attempt to reload from disk
        if not self.queue:
            self._load_from_disk()
            
        if self.queue:
            return self.queue.popleft()
        return None

    def _spill_to_disk(self):
        """Moves the back-half of the queue to disk to free up RAM."""
        spill_count = len(self.queue) // 2
        self.logger.warning(f"Memory queue full! Spilling the last {spill_count} URLs to disk...")
        
        # Temporarily convert to list for precise slicing and maintaining BFS order
        queue_list = list(self.queue)
        keep_in_mem = queue_list[:-spill_count]
        spill_to_disk = queue_list[-spill_count:]
        
        self.queue = deque(keep_in_mem)
        
        # Save the second half of the queue to the end of the spill file
        with open(self.spill_file, "a", encoding="utf-8") as f:
            for url in spill_to_disk:
                f.write(url + "\n")

    def _load_from_disk(self):
        """Loads URLs back from disk when RAM queue is empty."""
        if not os.path.exists(self.spill_file):
            return
            
        self.logger.info("Memory queue empty. Retrieving URLs from disk...")
        with open(self.spill_file, "r", encoding="utf-8") as f:
            lines = f.readlines()
        
        # Restore data to memory up to the maximum allowed capacity
        load_count = min(len(lines), self.max_memory_size)
        for i in range(load_count):
            self.queue.append(lines[i].strip())
            
        # Update the disk file (remove the lines that were transferred to memory)
        remaining_lines = lines[load_count:]
        if remaining_lines:
            with open(self.spill_file, "w", encoding="utf-8") as f:
                f.writelines(remaining_lines)
        else:
            os.remove(self.spill_file)