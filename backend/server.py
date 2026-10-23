"""Servidor local da interface compilada e API, somente com a biblioteca padrão."""

import argparse
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
from urllib.parse import urlsplit

from .beam import ValidationError, calculate
from verification.report import run_validation

DIST = Path(__file__).resolve().parent.parent / "dist"
MAX_BODY_BYTES = 16_384


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(DIST), **kwargs)

    def end_headers(self):
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'")
        super().end_headers()

    def json_response(self, status: int, data: dict):
        body = json.dumps(data, allow_nan=False, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if urlsplit(self.path).path == "/api/health":
            self.json_response(200, {"status": "ok", "version": "0.2.1"})
            return
        if urlsplit(self.path).path == "/api/validation":
            self.json_response(200, run_validation())
            return
        if urlsplit(self.path).path not in {"/", "/index.html", "/app.js", "/styles.css"}:
            self.json_response(404, {"error": "Recurso não encontrado."})
            return
        super().do_GET()

    def do_POST(self):
        if urlsplit(self.path).path != "/api/calculate":
            self.json_response(404, {"error": "Recurso não encontrado."})
            return
        if self.headers.get_content_type() != "application/json":
            self.json_response(415, {"error": "Envie os dados como application/json."})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            length = 0
        if not 0 < length <= MAX_BODY_BYTES:
            self.json_response(413, {"error": "Tamanho de requisição inválido (máximo 16 KiB)."})
            return
        try:
            payload = json.loads(self.rfile.read(length))
            result = calculate(payload)
        except (json.JSONDecodeError, UnicodeDecodeError):
            self.json_response(400, {"error": "JSON inválido."})
            return
        except ValidationError as exc:
            self.json_response(422, {"error": str(exc)})
            return
        self.json_response(200, result)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    if not (DIST / "index.html").is_file():
        parser.error("Interface ausente. Execute npm ci e npm run build primeiro.")
    server = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"Estrutura iniciado na porta {server.server_port}. Ctrl+C para encerrar.", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
