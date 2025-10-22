# ShadowGate

[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Repo](https://img.shields.io/badge/github-alimghmi%2FShadowGate-lightgrey.svg)](https://github.com/alimghmi/ShadowGate)

ShadowGate is a fast, async-driven web reconnaissance and exposure scanner for detecting admin panels, login interfaces, and misconfigured endpoints across single or multiple targets — built for professional penetration testers and security researchers.

> ⚠️ **Authorized testing only.** You must have explicit permission to scan any target.

---

## Overview

ShadowGate combines concurrency, user-agent rotation, proxy routing, and response classification to efficiently identify potentially exposed web interfaces.  
It provides structured output (NDJSON/JSON/CSV) suitable for pipelines and automation.

Key features:
- Async scanning engine for high-speed probing.
- Multiple routing modes: direct, proxy list, Tor.
- Customizable wordlists, user-agents, and status-code filters.
- Progress bar and interactive output using **Rich**.
- Machine-readable formats: `ndjson`, `json`, `csv`.
- Legal disclaimers and safety controls to discourage misuse.

---

<!-- ## Badges & Demo

![demo placeholder](docs/demo.gif)

--- -->

## Installation

```bash
git clone https://github.com/alimghmi/ShadowGate.git
cd ShadowGate
pip install -e .
```

Or (future):

```bash
pip install shadowgate
```

Requirements: **Python 3.10+**

---

## Quickstart

Basic CLI syntax:

```bash
python -m shadowgate.cli [GLOBAL FLAGS] COMMAND [OPTIONS]
```

Example:

```bash
python -m shadowgate.cli scan -t https://example.com --assume-legal
```

### Global options

- `-v`, `-vv` — Increase verbosity (info/debug).
- `--quiet` — Suppress non-error logs.
- `--version` — Show version and exit.

---

## Commands

### `scan`

Probe target(s) for exposed admin/login panels.

Examples:

```bash
# Single target
shadowgate scan -t example.com --assume-legal

# Multiple targets
shadowgate scan --targets targets.txt --assume-legal

# Custom wordlist and user agents
shadowgate scan -t example.com --wordlist common.txt --random-ua --assume-legal

# Save results to file (JSON)
shadowgate scan -t example.com --out json --output results.json --assume-legal

# Route traffic via Tor
shadowgate scan -t example.com --tor --assume-legal
```

Options summary (high level):

- `-t, --target` : Single URL or domain
- `--targets` : File with one target per line
- `--wordlist` : Override built-in wordlist
- `--useragents` : Override built-in user-agents
- `--proxies` / `--proxy` : File or inline proxy(s)
- `--tor` : Route traffic via Tor
- `--status-codes` : Acceptable response codes (e.g., `200,3xx,401-403`)
- `--rps` : Requests per second (default: 10)
- `--concurrency` : Number of in-flight requests
- `--timeout` : Per-request timeout (seconds)
- `--retries` : Retry attempts
- `--follow-redirects` : Follow HTTP redirects
- `--random-ua` : Rotate User-Agent headers
- `--insecure` : Disable TLS verification (warning shown)
- `--out` : Output format (`ndjson`, `json`, `csv`, `table`)
- `--output` : Save results to file
- `--assume-legal` : Confirm you have authorization

---

## Output formats

- `ndjson` — Newline-delimited JSON (recommended for pipelines)
- `json` — Pretty JSON
- `csv` — Spreadsheet-compatible
- `table` — Human-readable Rich table

Example NDJSON line:

```json
{"url":"https://example.com/admin/","status":200,"ok":true,"error":null,"elapsed":0.123}
```

---

## Logging & Debugging

Control verbosity with `-v`:

```bash
# Info-level logs
shadowgate -v scan -t example.com --assume-legal

# Debug with tracebacks
shadowgate -vv scan -t example.com --assume-legal
```

Logs and progress/status output are written to STDERR; scan results are emitted to STDOUT (so they can be piped or saved).

---

## Architecture (brief)

- `cli.py` — Typer-based CLI with Rich output and logging controls.
- `engine.py` — Asynchronous scanning engine handling requests, rate-limiting, and result collection.
- `utils.py` — Wordlists, user-agents, helper utilities.
- `wordlists/` — Default wordlists and payloads.

The CLI isolates control-plane logs (stderr) from data-plane output (stdout), enabling safe automation and piping.

---

## Legal & Ethics

ShadowGate is intended **for authorized security testing and research only**. Unauthorized scanning may be illegal and unethical. Always obtain written permission before testing.

Use the bundled legal command to show the short disclaimer:

```bash
shadowgate legal
```

---

## Contributing

Contributions are welcome.

1. Fork the repository
2. Create a branch (`git checkout -b feature/your-feature`)
3. Open a Pull Request

Please include tests and documentation for new features.

---

## License

MIT License © Ali Moghimi  
See `LICENSE` for details.

---

## Acknowledgements & References

- Inspired by tools like `ffuf`, `dirsearch`, and `nmap`.
- Built with: [Typer](https://typer.tiangolo.com), [Rich](https://github.com/Textualize/rich)

---
