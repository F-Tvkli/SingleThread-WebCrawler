# Single-Threaded Web Crawler

A highly optimized, single-threaded web crawler designed to traverse and download web pages from a target domain. This project is implemented in Python and focuses on network efficiency, robust memory management, and clean architecture.

## Project Architecture

The crawler is divided into three core modules managed by a central orchestrator:

1. **URL Frontier (`frontier.py`)**
   - **Queue Management:** Utilizes `collections.deque` for $O(1)$ Breadth-First Search (BFS) traversal.
   - **UChecker (Deduplication):** Uses Python `set` for $O(1)$ lookup time to ensure URLs are processed exactly once.
   - **Hybrid Memory/Disk Engine:** Automatically spills excess queue data to disk (`queue_spill.txt`) when RAM capacity is reached, preventing `MemoryError` during large crawls.

2. **Network Fetcher (`fetcher.py`)**
   - **Connection Pooling:** Uses `requests.Session()` to reuse TCP connections, significantly reducing network latency in single-threaded mode.
   - **Bandwidth Optimization:** Implements HTTP `HEAD` pre-flight requests to verify `Content-Type`. Only `text/html` payloads are downloaded, ignoring large media or binary files.
   - **Robust Error Handling:** Built-in retry mechanisms with exponential backoff for handling transient network failures (e.g., 500, 502, 503, 504 errors).

3. **HTML Parser (`parser.py`)**
   - Uses `BeautifulSoup4` with the standard `html.parser` for DOM traversal.
   - Normalizes extracted URLs by converting relative paths to absolute URLs (`urljoin`) and stripping URL fragments (`urldefrag`) to maintain structural consistency and prevent logical duplication.

## Hardware & System Limits
As per the project requirements, the crawler is strictly single-threaded and capped at downloading **10,000 pages** from a single domain without duplication.

## Installation

Ensure you have Python 3.8+ installed. Install the required dependencies:

```bash
pip install -r requirements.txt