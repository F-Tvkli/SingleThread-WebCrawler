import os
import sys
import time
import logging
from frontier import URLFrontier
from fetcher import Fetcher
from parser import Parser

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("crawler_engine.log", encoding="utf-8")
    ]
)
logger = logging.getLogger(__name__)

def get_directory_size_mb(directory: str) -> float:
    total_size = 0
    for dirpath, _, filenames in os.walk(directory):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            if not os.path.islink(fp):
                total_size += os.path.getsize(fp)
    return total_size / (1024 * 1024)

def main():
    # Targeted Production Environment
    TARGET_DOMAIN = "torob.com"
    START_URL = "https://torob.com/"
    MAX_PAGES = 10000
    SAVE_DIR = "crawled_html_files"
    USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"

    os.makedirs(SAVE_DIR, exist_ok=True)
    
    frontier = URLFrontier(base_domain=TARGET_DOMAIN, user_agent=USER_AGENT, max_depth=10)
    
    # Passing the anti-bot delays (between 1.5 to 3.5 seconds per request)
    fetcher = Fetcher(timeout=10, min_delay=1.5, max_delay=3.5)
    
    frontier.add_url(START_URL, depth=0)
    downloaded_count = 0
    start_time = time.time()

    logger.info(f"Booting single-threaded crawler engine targeting {TARGET_DOMAIN}")
    logger.info("-" * 60)

    try:
        while downloaded_count < MAX_PAGES:
            next_node = frontier.get_next_url()
            if not next_node:
                logger.info("Graph traversal complete. Queue is empty.")
                break
                
            current_url, current_depth = next_node
            
            html_content = fetcher.fetch_html(current_url)
            if not html_content:
                continue
                
            file_name = f"page_{downloaded_count + 1:05d}.html"
            file_path = os.path.join(SAVE_DIR, file_name)
            
            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(f"<!-- Source URL: {current_url} | Depth: {current_depth} -->\n")
                    f.write(html_content)
            except IOError as e:
                logger.error(f"I/O Exception on write: {e}")
                continue
                
            downloaded_count += 1
            logger.info(f"[NODE EXECUTED] {downloaded_count}/{MAX_PAGES} | Depth: {current_depth} | URL: {current_url}")

            new_links = Parser.extract_links(html_content, current_url)
            for link in new_links:
                frontier.add_url(link, depth=current_depth + 1)

    except KeyboardInterrupt:
        logger.warning("\nManual override triggered. Halting engine safely...")
    except Exception as e:
        logger.error(f"Critical engine failure: {e}", exc_info=True)
    finally:
        total_time = time.time() - start_time
        dir_size_mb = get_directory_size_mb(SAVE_DIR)
        
        logger.info("\n" + "="*60)
        logger.info("CRAWLER ENGINE TELEMETRY REPORT")
        logger.info("="*60)
        logger.info(f"System Uptime        : {total_time:.2f} seconds")
        logger.info(f"Data Payload Size    : {dir_size_mb:.2f} MB")
        logger.info(f"Nodes Persisted      : {downloaded_count}")
        logger.info(f"Unique URLs Parsed   : {frontier.discovered_count}")
        logger.info(f"Backlog Node Count   : {len(frontier.queue)}")
        logger.info(f"Network Faults       : {fetcher.errors}")
        logger.info("="*60)

if __name__ == "__main__":
    main()