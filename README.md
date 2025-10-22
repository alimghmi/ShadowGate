# ShadowGate

**ShadowGate** is an asynchronous **admin panel and directory discovery tool** built for penetration testers and security researchers.  
It performs high-speed directory enumeration using async HTTP requests, customizable wordlists, and flexible status code filtering.

---

## Features

- **Asynchronous scanning** powered by `httpx` and `asyncio`
- **SOCKS5 / Tor proxy support**
- **Retry and rate limiting**
- **Status code–based filtering**
- **Structured CLI output and progress tracking**
- **Custom wordlists and configuration support**
- Compatible with **Python 3.10+**

---

## Installation

From source:

```bash
git clone https://github.com/alimghmi/ShadowGate.git
cd shadowgate
pip install -e .[dev]

python -m shadowgate.cli scan -t https://example.com --assume-legal
```

Or


```bash
pip install shadowgate
```

---

## Basic Usage

Scan a target domain for potential admin panels:

```bash
shadowgate scan -t https://example.com --assume-legal
```

Run with increased concurrency and custom timeout:

```bash
shadowgate scan -t https://example.com --rps 25 --timeout 10
```

Follow redirects and use random user agents:

```bash
shadowgate scan -t https://example.com --follow-redirects --random-ua
```

Use a proxy or route through Tor:

```bash
shadowgate scan -t https://example.com --proxy socks5://127.0.0.1:9050
# or
shadowgate scan -t https://example.com --tor
```

Save results to a file:

```bash
shadowgate scan -t https://example.com --assume-legal > results.txt
```

---

## Options

| Option | Description |
|--------|-------------|
| `-t, --target` | Target URL or domain |
| `--rps` | Requests per second (default: 10) |
| `--timeout` | Timeout per request (seconds) |
| `--retries` | Retry attempts on failure |
| `--random-ua` | Use random User-Agents |
| `--follow-redirects` | Follow HTTP redirects |
| `--tor` | Route requests through Tor (SOCKS5) |
| `--proxy` | Custom proxy URL (HTTP/SOCKS) |
| `--assume-legal` | Required confirmation for active scanning |

---

## Development

Run linting and tests:

```bash
ruff check .
pytest
```

---

## License

**MIT License** — use responsibly.  
Unauthorized scanning of systems without explicit permission is strictly prohibited.
