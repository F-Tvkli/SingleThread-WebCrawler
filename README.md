# High-Performance Single-Threaded Web Crawler

A highly optimized, single-threaded web crawler engineered in Python. Designed for high-throughput link extraction, aggressive memory management, and robust anti-bot resilience when crawling production environments.

## 🏗️ Project Architecture

The crawler strictly adheres to classic Information Retrieval (IR) concepts and is decoupled into three core modules managed by a central orchestrator:

1. **URL Frontier (`frontier.py`)**
   - **Queue Management:** Utilizes `collections.deque` for $O(1)$ Breadth-First Search (BFS) graph traversal.
   - **Polite Scheduling:** Implements a robust, `requests`-based `robots.txt` parser. Enforces strict fail-safe rules (defaults to Disallow-All on network failures) to prevent blind crawling.
   - **UChecker (Deduplication):** Uses Python `set` for $O(1)$ lookups and canonicalizes URLs (stripping fragments) to ensure nodes are processed exactly once.
   - **Hybrid Memory/Disk Engine:** Automatically spills excess queue data to physical disk (`queue_spill.txt`) when RAM capacity is breached, preventing `MemoryError` during exponential graph growth.

2. **Network Fetcher (`fetcher.py`)**
   - **Application-Level DNS Caching:** Intercepts `socket.getaddrinfo` to cache IP resolutions in-memory, bypassing redundant OS-level DNS lookups and maximizing single-threaded throughput.
   - **Anti-Bot Resilience:** Implements randomized politeness delays (1.5s - 3.5s) and realistic `User-Agent` masquerading to evade Web Application Firewalls (WAF) and IP blocking in production environments.
   - **Connection Pooling & Pre-flight:** Uses `requests.Session()` to hold TCP connections open. Executes HTTP `HEAD` requests to verify `Content-Type: text/html` before downloading payloads, saving bandwidth.

3. **HTML Parser (`parser.py`)**
   - **Memory-Optimized Parsing:** Replaces full DOM tree construction with `SoupStrainer`, forcing `BeautifulSoup4` to parse only `<a>` tags. This drastically reduces CPU cycles and RAM leakage during deep crawls.
   - **Link Extraction:** Normalizes extracted links by resolving relative paths to absolute URLs via `urljoin`.

## ⚙️ Hardware & System Limits
As per project requirements, the engine operates on a single thread and is capped at successfully persisting **10,000 pages** from a single domain. Downloaded pages are stored locally with their source URLs injected as HTML comments. 

*During live telemetry testing against production environments (`torob.com`), the engine gracefully handled 456 WAF blocks over 70 minutes, successfully parsing 24,149 unique URLs and persisting 770 payloads without crashing.*

## 🚀 Installation & Usage

Ensure you have Python 3.8+ installed. 

1. Install the required dependencies:
```bash
pip install -r requirements.txt