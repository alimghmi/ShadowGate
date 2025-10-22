from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import re
import sys
import time
from collections.abc import Sequence
from pathlib import Path
from urllib.parse import urlsplit

import typer
from rich.console import Console
from rich.logging import RichHandler
from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    SpinnerColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
)

from .engine import Engine
from .utils import UserAgent, WordsListLoader

app = typer.Typer(no_args_is_help=True)
console = Console()
err_console = Console(stderr=True)

__version__ = "0.1.0"


class StripTracebacksFilter(logging.Filter):
    """Remove exc_info from log records unless we're in DEBUG.

    This prevents ugly tracebacks for end-users even if code logs exc_info=True.
    """

    def __init__(self, debug_enabled: bool):
        super().__init__()
        self.debug_enabled = debug_enabled

    def filter(self, record: logging.LogRecord) -> bool:
        if not self.debug_enabled:
            record.exc_info = None
        return True


def _configure_logging(
    level: int = logging.INFO, debug_tracebacks: bool = False
) -> None:
    """Attach a Rich handler that writes to STDERR, and silence noisy libs.
    """
    pkg_logger = logging.getLogger("shadowgate")
    pkg_logger.setLevel(level)
    for h in list(pkg_logger.handlers):
        pkg_logger.removeHandler(h)

    handler = RichHandler(
        show_time=True,
        show_level=True,
        show_path=False,
        rich_tracebacks=debug_tracebacks,  # only when -vv
        markup=True,
        console=err_console,  # logs -> STDERR
    )
    handler.setFormatter(logging.Formatter("%(message)s"))
    handler.addFilter(StripTracebacksFilter(debug_tracebacks))
    pkg_logger.addHandler(handler)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("tenacity").setLevel(logging.WARNING)


_SC_TOKEN = re.compile(r"^\d{3}$|^[1-5]xx$|^\d{3}-\d{3}$")


def _parse_status_codes(exprs: Sequence[str]) -> list[int]:
    """Accept tokens like: 200, 3xx, 401-403
    
    Provided as multiple flags or a single comma-joined string.
    """
    tokens: list[str] = []
    if len(exprs) == 1 and "," in exprs[0]:
        tokens = [t.strip() for t in exprs[0].split(",") if t.strip()]
    else:
        tokens = list(exprs)

    out: set[int] = set()
    for tok in tokens:
        if not _SC_TOKEN.match(tok):
            raise typer.BadParameter(f"Invalid status code token: {tok}")
        if tok.endswith("xx"):
            base = int(tok[0]) * 100
            out.update(range(base, base + 100))
        elif "-" in tok:
            a, b = map(int, tok.split("-", 1))
            if not (100 <= a <= b <= 599):
                raise typer.BadParameter(f"Range out of bounds: {tok}")
            out.update(range(a, b + 1))
        else:
            out.add(int(tok))
    return sorted(out)


def _normalize_url(u: str) -> str:
    u = u.strip()
    if not u:
        return u
    parts = urlsplit(u)
    return u if parts.scheme else f"https://{u}"


def _read_lines(path: Path) -> list[str]:
    if not path.exists():
        raise typer.BadParameter(f"file not found: {path}")
    return [
        ln.strip() for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()
    ]


def _count_file_lines(p: Path | None) -> int:
    if not p:
        return 0
    try:
        return sum(1 for _ in p.open("r", encoding="utf-8"))
    except Exception:
        return 0


def _tor_proxy_default() -> str:
    return "socks5h://127.0.0.1:9050"


@app.callback(invoke_without_command=True)
def _global(
    version: bool = typer.Option(
        False, "--version", help="Show version and exit.", is_eager=True
    ),
    verbose: int = typer.Option(0, "-v", count=True, help="-v=INFO, -vv=DEBUG"),
    quiet: bool = typer.Option(False, "--quiet", help="Only errors"),
):
    """ShadowGate CLI.
    
    Global flags must come before commands:
      python -m shadowgate.cli -v scan -t https://example.com --assume-legal
    """
    if version:
        typer.echo(__version__)
        raise typer.Exit()

    level = (
        logging.ERROR
        if quiet
        else (
            logging.INFO
            if verbose == 1
            else logging.DEBUG if verbose >= 2 else logging.WARNING
        )
    )
    _configure_logging(level=level, debug_tracebacks=(verbose >= 2))


@app.command()
def legal():
    """Show a short legal disclaimer."""
    err_console.print(
        "[bold]Authorized testing only.[/] Do not scan systems without explicit permission."
    )


@app.command()
def scan(
    target: str | None = typer.Option(
        None, "--target", "-t", help="Single URL or domain"
    ),
    targets_file: Path | None = typer.Option(
        None, "--targets", help="File with one target per line"
    ),
    wordlist: Path | None = typer.Option(
        None, "--wordlist", help="Override built-in wordlist"
    ),
    useragents: Path | None = typer.Option(
        None, "--useragents", help="Override built-in user-agents"
    ),
    # routing
    proxies: Path | None = typer.Option(
        None, "--proxies", help="File with one proxy per line"
    ),
    proxy: list[str] = typer.Option(
        [],
        "--proxy",
        help="Explicit proxy URL (repeatable). E.g. http://1.2.3.4:8080 or socks5h://127.0.0.1:9050",
    ),
    tor: bool = typer.Option(
        False, "--tor/--no-tor", help="Route traffic via Tor (SOCKS5H)"
    ),
    tor_proxy: str | None = typer.Option(
        None,
        "--tor-proxy",
        help="Override Tor SOCKS URL (default socks5h://127.0.0.1:9050)",
    ),
    status_codes: list[str] = typer.Option(
        ["200", "301", "302", "401-403"],
        "--status-codes",
        help="Comma list or tokens: 200,3xx,401-403",
    ),
    concurrency: int = typer.Option(
        10, "--concurrency", min=1, max=200, help="In-flight requests"
    ),
    rps: int = typer.Option(10, "--rps", min=1, max=100, help="Requests per second"),
    timeout: float = typer.Option(
        5.0, "--timeout", min=0.1, help="Per-request timeout (seconds)"
    ),
    retries: int = typer.Option(1, "--retries", min=0, max=10, help="Retry attempts"),
    follow_redirects: bool = typer.Option(
        False, "--follow-redirects/--no-follow-redirects", help="Follow HTTP redirects"
    ),
    random_useragent: bool = typer.Option(
        True, "--random-ua/--no-random-ua", help="Rotate User-Agent"
    ),
    insecure: bool = typer.Option(
        False, "--insecure", help="Bypass TLS verification (warning will be shown)"
    ),
    out: str = typer.Option(
        "ndjson", "--out", help="table|json|ndjson|csv  (default: ndjson)"
    ),
    output: Path | None = typer.Option(
        None, "--output", help="Write results to file instead of STDOUT"
    ),
    progress: bool = typer.Option(
        True, "--progress/--no-progress", help="Show progress bar (default: on)"
    ),
    echo_found: bool = typer.Option(
        True,
        "--echo-found/--no-echo-found",
        help="Print FOUND lines as they happen (default: on)",
    ),
    summary: bool = typer.Option(
        True,
        "--summary/--no-summary",
        help="Print end-of-run summary to STDERR (default: on)",
    ),
    # legal
    assume_legal: bool = typer.Option(
        False, "--assume-legal", help="Confirm you have authorization"
    ),
):
    """Probe target(s) for exposed admin/login panels.
    Defaults: progress ON, machine-friendly NDJSON to STDOUT, logs to STDERR.
    """
    if not assume_legal:
        err_console.print(
            "[bold red]Authorized testing only.[/] Re-run with --assume-legal if you have explicit permission."
        )
        raise typer.Exit(code=2)

    targets: list[str] = []
    if target:
        targets.append(_normalize_url(target))
    if targets_file:
        targets.extend(_normalize_url(t) for t in _read_lines(targets_file))
    if not targets:
        err_console.print("[yellow]No targets provided. Use --target or --targets.[/]")
        raise typer.Exit(code=2)

    wpath = wordlist if wordlist else WordsListLoader.WORDSLIST_PATH
    upath = useragents if useragents else UserAgent.USERAGENTS_PATH

    try:
        status_codes_parsed = _parse_status_codes(status_codes)
    except typer.BadParameter as e:
        err_console.print(f"[red]{e}[/]")
        raise typer.Exit(code=2)

    if proxies and (proxy or tor):
        err_console.print(
            "[red]--proxies cannot be used with --proxy or --tor. Choose one routing mode.[/]"
        )
        raise typer.Exit(code=2)
    if tor and proxy:
        err_console.print(
            "[red]--tor cannot be used together with --proxy. Choose one routing mode.[/]"
        )
        raise typer.Exit(code=2)

    proxies_arg: Path | list[str] | None = None
    if proxies:
        proxies_arg = proxies
        err_console.print(f"Proxy mode: file ({_count_file_lines(proxies)} entries)")
    elif proxy:
        proxies_arg = list(proxy)
        err_console.print(f"Proxy mode: inline ({len(proxy)} entries)")
    elif tor:
        tor_url = tor_proxy or _tor_proxy_default()
        proxies_arg = [tor_url]
        err_console.print(f"Proxy mode: Tor ({tor_url})")

    if insecure:
        err_console.print(
            "[yellow]Warning:[/] TLS verification is disabled (--insecure)."
        )

    t0 = time.perf_counter()
    findings_total = 0
    errors_total = 0

    for tgt in targets:
        err_console.rule(f"Target {tgt}")
        ok = asyncio.run(
            _preflight_reachability(
                tgt,
                wpath,
                upath,
                proxies_arg,
                timeout,
                rps,
                status_codes_parsed,
                random_useragent,
                retries,
                concurrency,
                follow_redirects,
                insecure,
                progress,
            )
        )
        if not ok:
            err_console.print("[red]Preflight failed. Skipping target.[/]")
            continue

        nf_code = asyncio.run(
            _preflight_not_found(
                tgt,
                wpath,
                upath,
                proxies_arg,
                timeout,
                rps,
                status_codes_parsed,
                random_useragent,
                retries,
                concurrency,
                follow_redirects,
                insecure,
                progress,
            )
        )
        if nf_code is not None and nf_code in status_codes_parsed:
            err_console.print(
                f"[yellow]Note:[/] dropping host not-found {nf_code} from interesting set"
            )
            status_codes_parsed.remove(nf_code)

        findings, errors = asyncio.run(
            _run_one_target(
                tgt,
                wpath,
                upath,
                proxies_arg,
                timeout,
                rps,
                status_codes_parsed,
                random_useragent,
                retries,
                concurrency,
                follow_redirects,
                insecure,
                out,
                output,
                progress,
                echo_found,
            )
        )
        findings_total += findings
        errors_total += errors

    if summary:
        err_console.print(
            f"[bold]Done.[/] Elapsed: {time.perf_counter() - t0:.2f}s | Findings: {findings_total} | Errors: {errors_total}"
        )
    raise typer.Exit(code=2 if errors_total else (1 if findings_total else 0))


async def _preflight_reachability(
    url: str,
    wordlist: Path,
    useragents: Path,
    proxies: Path | list[str] | None,
    timeout: float,
    rps: float,
    status_codes: list[int],
    random_useragent: bool,
    retries: int,
    concurrency: int,
    follow_redirects: bool,
    insecure: bool,
    show_status: bool,
) -> bool:
    with (
        err_console.status("Preflight: checking reachability...", spinner="dots")
        if show_status
        else contextlib.nullcontext()
    ):
        eng = Engine(
            url=url,
            wordslist_path=wordlist,
            useragents_path=useragents,
            proxies=proxies,
            timeout=int(timeout),
            status_codes=list(status_codes),
            random_useragent=random_useragent,
            retries=retries,
            semaphore_count=concurrency,
            follow_redirects=follow_redirects,
            rps=rps,
            insecure=insecure,
        )
        try:
            ok = await eng.check_target()
        finally:
            await eng.c.close()
        if not ok and not show_status:
            err_console.print("Preflight: target unreachable (use -vv for details)")
        elif ok and show_status:
            err_console.print("Preflight: reachable")
        return ok


async def _preflight_not_found(
    url: str,
    wordlist: Path,
    useragents: Path,
    proxies: Path | list[str] | None,
    timeout: float,
    rps: float,
    status_codes: list[int],
    random_useragent: bool,
    retries: int,
    concurrency: int,
    follow_redirects: bool,
    insecure: bool,
    show_status: bool,
) -> int | None:
    with (
        err_console.status(
            "Preflight: detecting host not-found code...", spinner="dots"
        )
        if show_status
        else contextlib.nullcontext()
    ):
        eng = Engine(
            url=url,
            wordslist_path=wordlist,
            useragents_path=useragents,
            proxies=proxies,
            timeout=int(timeout),
            status_codes=list(status_codes),
            random_useragent=random_useragent,
            retries=retries,
            semaphore_count=concurrency,
            follow_redirects=follow_redirects,
            rps=rps,
            insecure=insecure,
        )
        try:
            nf = await eng.get_not_found_status_code()
        finally:
            await eng.c.close()
        if show_status and nf is not None:
            err_console.print(f"Preflight: host not-found {nf}")
        return nf


async def _run_one_target(
    url: str,
    wordlist: Path,
    useragents: Path,
    proxies: Path | list[str] | None,
    timeout: float,
    rps: float,
    status_codes: list[int],
    random_useragent: bool,
    retries: int,
    concurrency: int,
    follow_redirects: bool,
    insecure: bool,
    out: str,
    output: Path | None,
    show_progress: bool,
    echo_found: bool,
) -> tuple[int, int]:
    """Run a single target. By default: show progress and 'FOUND' to STDERR.
    STDOUT only receives the chosen data output.
    """
    engine = Engine(
        url=url,
        wordslist_path=wordlist,
        useragents_path=useragents,
        proxies=proxies,
        timeout=int(timeout),
        status_codes=status_codes,
        random_useragent=random_useragent,
        retries=retries,
        semaphore_count=concurrency,
        follow_redirects=follow_redirects,
        rps=rps,
        insecure=insecure,
    )

    maybe_progress = (
        Progress(
            SpinnerColumn(),
            "[progress.description]{task.description}",
            BarColumn(),
            MofNCompleteColumn(),
            TimeElapsedColumn(),
            TimeRemainingColumn(),
            transient=False,
            console=err_console,
        )
        if show_progress
        else contextlib.nullcontext()
    )

    total = len(getattr(engine, "built_urls", [])) or 1
    findings = 0
    errors = 0

    async def _monitor_found(task_id: int | None) -> None:
        last_done = 0
        last_found_count = 0
        while engine.on:
            if not engine.tasks:
                await asyncio.sleep(0.05)
                continue

            if show_progress and task_id is not None:
                done = sum(1 for t in engine.tasks if t.done())
                if done != last_done:
                    # type: ignore[attr-defined]
                    maybe_progress.update(task_id, completed=done)  # pyright: ignore
                    last_done = done

            if echo_found:
                found_now = len(engine.found_urls)
                if found_now > last_found_count:
                    for p in engine.found_urls[last_found_count:found_now]:
                        err_console.print(f"[green]FOUND[/] {p}")
                    last_found_count = found_now

            if engine.tasks and all(t.done() for t in engine.tasks):
                break
            await asyncio.sleep(0.05)

    async def _run_engine():
        return await engine.run()

    if show_progress:
        with maybe_progress:  # type: ignore[attr-defined]
            task_id = maybe_progress.add_task("Probing", total=total)  # type: ignore[attr-defined]
            monitor_task = asyncio.create_task(_monitor_found(task_id))
            try:
                results = await _run_engine()
            finally:
                engine.on = False
                with contextlib.suppress(Exception):
                    await monitor_task
    else:
        monitor_task = asyncio.create_task(_monitor_found(None))
        try:
            results = await _run_engine()
        finally:
            engine.on = False
            with contextlib.suppress(Exception):
                await monitor_task

    # present results to STDOUT in chosen format
    _render_results(results, status_codes, out, output)

    _elapsed = 0.0
    for _u, r in results:
        if getattr(r, "elapsed", None):
            _elapsed += float(r.elapsed)
        if getattr(r, "error", None):
            errors += 1
        elif getattr(r, "status", None) in status_codes:
            findings += 1

    if show_progress:
        err_console.print(f"[green]Findings:[/] {findings}    [red]Errors:[/] {errors}")
        if total:
            err_console.print(f"~ {round(_elapsed / total, 2)} sec/req")
    return findings, errors


def _render_results(
    results,
    status_codes: list[int],
    out: str,
    output: Path | None,
) -> None:
    """Send data to STDOUT only. All logs/status remained on STDERR.
    """
    if out == "table":
        from rich.table import Table

        table = Table(title="ShadowGate Results")
        table.add_column("URL")
        table.add_column("Status")
        table.add_column("Interesting")
        table.add_column("Error")
        table.add_column("Elapsed (s)")
        for url, r in results:
            table.add_row(
                url,
                str(getattr(r, "status", "")),
                "True" if getattr(r, "status", None) in status_codes else "False",
                getattr(r, "error", "") or "",
                (
                    f"{getattr(r, 'elapsed', 0.0):.3f}"
                    if getattr(r, "elapsed", None) is not None
                    else ""
                ),
            )
        console.print(table)
        return

    rows = []
    for url, r in results:
        rows.append(
            {
                "url": url,
                "status": getattr(r, "status", None),
                "ok": getattr(r, "status", None) in status_codes,
                "error": getattr(r, "error", None),
                "elapsed": getattr(r, "elapsed", None),
            }
        )

    fp = None
    try:
        if output:
            output.parent.mkdir(parents=True, exist_ok=True)
            fp = output.open("w", encoding="utf-8")
        else:
            fp = sys.stdout

        if out == "json":
            json.dump(rows, fp, ensure_ascii=False, indent=2)
            fp.write("\n")
        elif out == "ndjson":
            for row in rows:
                fp.write(json.dumps(row) + "\n")
        elif out == "csv":
            import csv

            w = csv.DictWriter(
                fp, fieldnames=["url", "status", "ok", "error", "elapsed"]
            )
            w.writeheader()
            for row in rows:
                w.writerow(row)
        else:
            for row in rows:
                fp.write(json.dumps(row) + "\n")
    finally:
        if fp is not None and fp is not sys.stdout:
            fp.close()
        if output:
            err_console.print(f"[green]Saved →[/] {output}")


if __name__ == "__main__":
    try:
        app()
    except KeyboardInterrupt:
        err_console.print("\n[yellow]Exiting gracefully[/]")
        raise
    except Exception as e:
        err_console.print(f"[red]Fatal:[/] {type(e).__name__}: {e}")
        raise SystemExit(2) from e
