"""Loopback-only HTTP service; uploads live only for one request."""

import hmac
import json
import secrets
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib.resources import files

from .delivery import csv_report, demo_dataset, html_report
from .engine import MAX_BYTES, ValidationError, analyze, parse_csv


class Handler(BaseHTTPRequestHandler):
    server_version = "MarketObservatory/1.0"

    def log_message(self, format, *args):
        pass

    def setup(self):
        super().setup()
        self.connection.settimeout(15)

    def send(self, status, body, content_type="application/json; charset=utf-8"):
        if isinstance(body, dict):
            body = json.dumps(body, allow_nan=False).encode()
        elif isinstance(body, str):
            body = body.encode()
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header(
            "Content-Security-Policy",
            "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'",
        )
        self.end_headers()
        self.wfile.write(body)

    def valid_host(self):
        return self.headers.get("Host") in {
            f"127.0.0.1:{self.server.server_port}",
            f"localhost:{self.server.server_port}",
        }

    def do_GET(self):
        if not self.valid_host():
            return self.send(403, {"error": "Host must be the loopback server address."})
        path = self.path.split("?", 1)[0]
        routes = {
            "/": ("index.html", "text/html; charset=utf-8"),
            "/app.js": ("app.js", "text/javascript; charset=utf-8"),
            "/csv-input.js": ("csv-input.js", "text/javascript; charset=utf-8"),
            "/style.css": ("style.css", "text/css; charset=utf-8"),
        }
        if path in routes:
            name, mime = routes[path]
            text = files("market_observatory").joinpath("static", name).read_text(encoding="utf-8")
            return self.send(200, text.replace("__RESEARCH_TOKEN__", self.server.token), mime)
        if path == "/api/demo":
            return self.send(
                200,
                {
                    "metadata": demo_dataset()["metadata"],
                    "csv": files("market_observatory")
                    .joinpath("data", "demo.csv")
                    .read_bytes()
                    .decode("utf-8"),
                },
            )
        return self.send(404, {"error": "Not found."})

    def do_POST(self):
        host = self.headers.get("Host", "")
        token = self.headers.get("X-Research-Token", "")
        if (
            not self.valid_host()
            or self.headers.get("Origin") != f"http://{host}"
            or not hmac.compare_digest(token.encode("utf-8"), self.server.token.encode("utf-8"))
        ):
            return self.send(403, {"error": "Use the app from its local server URL."})
        if self.path not in {"/api/analyze", "/api/inspect"}:
            return self.send(404, {"error": "Not found."})
        if self.headers.get("Content-Type", "").split(";")[0] != "application/json":
            return self.send(415, {"error": "Use application/json."})
        try:
            size = int(self.headers.get("Content-Length", "0"))
            if size <= 0 or size > MAX_BYTES + 65536:
                return self.send(
                    413,
                    {"error": "Request must be nonempty and at most 8 MiB plus metadata."},
                )
            payload = json.loads(self.rfile.read(size))
            if not isinstance(payload, dict):
                raise ValidationError("Request must be an object.")
            settings = payload.get("settings", {})
            allowed = {
                "symbols",
                "weights",
                "mode",
                "periods_per_year",
                "initial_value",
            }
            if not isinstance(settings, dict) or set(settings) - allowed:
                raise ValidationError("Unknown or invalid analysis settings.")
            if payload.get("demo") is True:
                dataset = demo_dataset()
            else:
                dataset = parse_csv(payload.get("csv"), payload.get("metadata"))
            if self.path == "/api/inspect":
                return self.send(
                    200,
                    {
                        "symbols": sorted(dataset["prices"]),
                        "metadata": dataset["metadata"],
                    },
                )
            result = analyze(dataset, **settings)
            self.send(
                200,
                {
                    "result": result,
                    "exports": {"csv": csv_report(result), "html": html_report(result)},
                },
            )
        except (ValueError, UnicodeError, RecursionError) as error:
            self.send(
                400,
                {
                    "error": str(error)
                    if isinstance(error, ValidationError)
                    else "Malformed JSON or request values."
                },
            )
        except TimeoutError:
            self.send(408, {"error": "Request timed out."})


class LocalServer(ThreadingHTTPServer):
    daemon_threads = True

    # Concurrent analyses are bounded; local requests cannot spawn unlimited compute.
    def __init__(self, *args, **kwargs):
        import threading

        self.slots = threading.BoundedSemaphore(4)
        super().__init__(*args, **kwargs)

    def process_request(self, request, client_address):
        if not self.slots.acquire(blocking=False):
            request.close()
            return
        try:
            super().process_request(request, client_address)
        except BaseException:
            self.slots.release()
            raise

    def process_request_thread(self, request, client_address):
        try:
            super().process_request_thread(request, client_address)
        finally:
            self.slots.release()


def create_server(port=8765):
    server = LocalServer(("127.0.0.1", port), Handler)
    server.token = secrets.token_urlsafe(32)
    return server
