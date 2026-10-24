"""Local results viewer: serves viewer/index.html and the contents of runs/ as JSON. Read-only.

Usage:
  python scripts/view_results.py                    # http://127.0.0.1:8765, opens a browser tab
  python scripts/view_results.py --runs-dir path/to/runs --port 9000 --no-browser

Routes:
  /                          the page (viewer/index.html)
  /api/summary[?models=M]    overview for one model set (default: the one with most runs; * = all):
                             spend, positive control, detector summary, held-out TPR/FPR
  /api/runs                  every run folder with its kind and headline fields
  /api/run/<run_id>          one run (game runs get every detector recomputed)
  /files/<run_id>/<path>     a file inside a run folder (images, markdown, logs)
Binds to 127.0.0.1 only. Results are recomputed when a run folder changes (no restart needed).
"""

from __future__ import annotations

import argparse
import json
import mimetypes
import sys
import threading
import traceback
import webbrowser
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

from netinf import viewer as v

PAGE = Path(__file__).resolve().parents[1] / "viewer" / "index.html"


def fingerprint(runs_dir: Path) -> tuple:
    """Changes whenever a run folder or one of its top-level files is added or written."""
    if not runs_dir.is_dir():
        return ()
    out = []
    for p in sorted(runs_dir.iterdir()):
        try:
            files = [(f.name, f.stat().st_mtime_ns, f.stat().st_size) for f in p.iterdir()] \
                if p.is_dir() else [(p.name, p.stat().st_mtime_ns, p.stat().st_size)]
        except OSError:
            continue
        out.append((p.name, tuple(sorted(files))))
    return tuple(out)


class Cache:
    def __init__(self, runs_dir: Path):
        self.runs_dir = runs_dir
        self.lock = threading.Lock()
        self.key, self.store = None, {}

    def get(self, name: str, fn):
        with self.lock:
            key = fingerprint(self.runs_dir)
            if key != self.key:
                self.key, self.store = key, {}
            if name not in self.store:
                self.store[name] = json.dumps(fn()).encode("utf-8")
            return self.store[name]


def make_handler(runs_dir: Path, cache: Cache):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt, *args):  # quieter than the default: errors only
            if args and str(args[1]).startswith(("4", "5")):
                sys.stderr.write(f"{self.address_string()} {fmt % args}\n")

        def send(self, body: bytes, ctype: str, status=HTTPStatus.OK):
            self.send_response(status)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def error(self, status, msg):
            self.send(json.dumps({"error": msg}).encode(), "application/json", status)

        def do_GET(self):
            url = urlparse(self.path)
            path = unquote(url.path)
            models = parse_qs(url.query).get("models", [None])[0]
            try:
                if path in ("/", "/index.html"):
                    return self.send(PAGE.read_bytes(), "text/html; charset=utf-8")
                if path == "/favicon.ico":  # the page carries an inline icon
                    return self.send(b"", "image/x-icon", HTTPStatus.NO_CONTENT)
                if path == "/api/summary":
                    return self.send(cache.get(f"summary:{models}",
                                               lambda: v.summary(runs_dir, models)),
                                     "application/json")
                if path == "/api/runs":
                    return self.send(cache.get("runs", lambda: v.list_runs(runs_dir)),
                                     "application/json")
                if path.startswith("/api/run/"):
                    rid = path[len("/api/run/"):]
                    return self.send(cache.get(f"run:{rid}", lambda: v.run_detail(runs_dir, rid)),
                                     "application/json")
                if path.startswith("/files/"):
                    rid, _, rel = path[len("/files/"):].partition("/")
                    base = v.resolve_run(runs_dir, rid)
                    f = (base / rel).resolve()
                    if base not in f.parents or not f.is_file():
                        raise FileNotFoundError(rel)
                    ctype = mimetypes.guess_type(f.name)[0] or "application/octet-stream"
                    if ctype.startswith("text/") or f.suffix in v.TEXT_SUFFIXES:
                        ctype = ("application/json" if f.suffix == ".json"
                                 else "text/plain") + "; charset=utf-8"
                    return self.send(f.read_bytes(), ctype)
                self.error(HTTPStatus.NOT_FOUND, f"no route {path}")
            except FileNotFoundError as e:
                self.error(HTTPStatus.NOT_FOUND, f"not found: {e}")
            except Exception as e:  # noqa: BLE001  show the failure in the page, not a dropped connection
                traceback.print_exc()
                self.error(HTTPStatus.INTERNAL_SERVER_ERROR, f"{type(e).__name__}: {e}")

    return Handler


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--runs-dir", type=Path, default=Path("runs"))
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--no-browser", action="store_true")
    args = ap.parse_args(argv)
    runs_dir = args.runs_dir.resolve()
    if not runs_dir.is_dir():
        print(f"no runs directory at {runs_dir}", file=sys.stderr)
        return 1
    server = ThreadingHTTPServer(("127.0.0.1", args.port), make_handler(runs_dir, Cache(runs_dir)))
    url = f"http://127.0.0.1:{server.server_port}/"
    print(f"viewing {runs_dir} at {url} (Ctrl+C to stop)")
    if not args.no_browser:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
