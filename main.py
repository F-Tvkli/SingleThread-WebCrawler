import os
import sys
import time
import logging
from frontier import URLFrontier
from fetcher import Fetcher
from parser import Parser

# Configure CLI Logging: Outputs to both Console and a Log File
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("crawler_execution.log", encoding="utf-8")
    ]
)
logger = logging.getLogger(__name__)

def get_directory_size_mb(directory: str) -> float:
    """Calculates total size of a directory in Megabytes."""
    total_size = 0
    for dirpath, _, filenames in os.walk(directory):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            if not os.path.islink(fp):
                total_size += os.path.getsize(fp)
    return total_size / (1024 * 1024)

def main():
    # Crawler Configuration
    TARGET_DOMAIN = "books.toscrape.com"
    START_URL = "https://books.toscrape.com/"
    MAX_PAGES = 10000
    SAVE_DIR = "crawled_html_files"

    # Create the output directory if it does not exist
    os.makedirs(SAVE_DIR, exist_ok=True)
    
    # Initialize Core Components
    frontier = URLFrontier(base_domain=TARGET_DOMAIN)
    fetcher = Fetcher()
    
    # Seed the crawler with the initial URL
    frontier.add_url(START_URL)
    downloaded_count = 0
    start_time = time.time()

    logger.info(f"Starting crawler for domain: {TARGET_DOMAIN}")
    logger.info(f"Target max pages: {MAX_PAGES}")
    logger.info(f"Output directory: {SAVE_DIR}/")
    logger.info("-" * 50)

    try:
        # Main Event Loop
        while downloaded_count < MAX_PAGES:
            current_url = frontier.get_next_url()
            
            # If queue is completely empty (even after attempting disk load)
            if not current_url:
                logger.warning("Queue is empty. No more URLs to crawl.")
                break
                
            # Network Request
            html_content = fetcher.fetch_html(current_url)
            
            if not html_content:
                continue
                
            # File I/O: Save the raw HTML to disk with a custom naming convention
            file_name = f"page_{downloaded_count + 1:05d}.html"
            file_path = os.path.join(SAVE_DIR, file_name)
            
            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    # Injecting original URL as a comment for documentation
                    f.write(f"<!-- Source URL: {current_url} -->\n")
                    f.write(html_content)
            except IOError as e:
                logger.error(f"File system error saving {file_name}: {e}")
                continue
                
            downloaded_count += 1
            logger.info(f"[SUCCESS] {downloaded_count}/{MAX_PAGES} | Fetched: {current_url}")

            # Parsing and Enqueuing
            new_links = Parser.extract_links(html_content, current_url)
            added_count = 0
            for link in new_links:
                # add_url returns True if the URL was new and added to the queue
                if frontier.add_url(link):
                    added_count += 1
            
            # Use debug level for link extraction to avoid cluttering the CLI
            logger.debug(f"Extracted {len(new_links)} URLs. Added {added_count} new unique URLs to queue.")

    except KeyboardInterrupt:
        logger.warning("\nCrawler interrupted by user (Ctrl+C).")
    except Exception as e:
        logger.error(f"Unexpected fatal error: {e}", exc_info=True)
    finally:
        # Calculate Final Analytics required by the assignment
        end_time = time.time()
        total_time = end_time - start_time
        dir_size_mb = get_directory_size_mb(SAVE_DIR)
        
        logger.info("\n" + "="*50)
        logger.info("CRAWL EXECUTION REPORT (HW1 Statistics)")
        logger.info("="*50)
        logger.info(f"Execution Time       : {total_time:.2f} seconds")
        logger.info(f"Output Volume        : {dir_size_mb:.2f} MB")
        logger.info(f"Downloaded Pages     : {downloaded_count}")
        logger.info(f"Discovered URLs      : {frontier.discovered_count} (including duplicates)")
        logger.info(f"Remaining Queue Size : {len(frontier.queue)}")
        logger.info(f"Total Network Errors : {fetcher.errors}")
        logger.info("="*50)

if __name__ == "__main__":
    main()