#!/usr/bin/env python3
"""
ValorAcción — Local proxy server (uses yfinance)
Run: python3 server.py
Then open: http://localhost:8765
"""

import json
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import os
import sqlite3
import uuid
import hashlib

PORT = 8765
HTML_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "index.html")
DB_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "database.db")

def init_db():
    with sqlite3.connect(DB_FILE) as conn:
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password_hash TEXT)''')
        c.execute('''CREATE TABLE IF NOT EXISTS sessions (token TEXT PRIMARY KEY, username TEXT)''')
        c.execute('''CREATE TABLE IF NOT EXISTS portfolios (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT, ticker TEXT, UNIQUE(username, ticker))''')
        conn.commit()

init_db()

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

try:
    import yfinance as yf
except ImportError:
    print("⚠️  Instalando yfinance… (solo la primera vez)")
    import subprocess, sys
    subprocess.check_call([sys.executable, "-m", "pip", "install", "yfinance", "-q"])
    import yfinance as yf


def get_stock_data(symbol: str) -> dict:
    ticker = yf.Ticker(symbol)
    info = ticker.info         # full fundamentals dict
    fast = ticker.fast_info    # lightweight realtime prices

    price = fast.last_price or info.get("regularMarketPrice") or info.get("currentPrice")
    if not price:
        raise ValueError(f"Precio no disponible para {symbol!r}")

    # Trailing EPS
    eps = info.get("trailingEps") or info.get("epsTrailingTwelveMonths")

    # Growth: earningsGrowth (YoY) preferred, else revenueGrowth, else default 8
    growth_raw = info.get("earningsGrowth") or info.get("revenueGrowth") or 0
    growth_pct = growth_raw * 100 if abs(growth_raw) < 1 else growth_raw
    growth_pct = float(max(min(growth_pct or 8, 40), 0.5))

    # FCF per share
    fcf_ps = None
    fcf = info.get("freeCashflow")
    shares = info.get("sharesOutstanding") or fast.shares
    if fcf and shares and shares > 0:
        fcf_ps = fcf / shares

    beta = float(info.get("beta") or 1.0)
    wacc = 0.043 + beta * 0.055

    change_pct = fast.last_price / fast.previous_close - 1 if fast.previous_close else 0
    change_pct *= 100

    return {
        "quoteResponse": {
            "result": [{
                "longName":                   info.get("longName") or info.get("shortName") or symbol,
                "symbol":                     symbol,
                "sector":                     info.get("sector") or info.get("industry") or "",
                "regularMarketPrice":         price,
                "epsTrailingTwelveMonths":    eps,
                "trailingPE":                 info.get("trailingPE"),
                "priceToBook":                info.get("priceToBook"),
                "bookValue":                  info.get("bookValue"),
                "returnOnEquity":             info.get("returnOnEquity"),
                "freeCashflow":               fcf,
                "sharesOutstanding":          shares,
                "regularMarketChangePercent": change_pct,
                "beta":                       beta,
                "earningsGrowth":             growth_raw,
                "revenueGrowth":              info.get("revenueGrowth"),
            }],
            "error": None,
        }
    }


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass # Silence logs

    def send_cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")

    def get_user_from_auth(self):
        auth = self.headers.get("Authorization")
        if not auth or not auth.startswith("Bearer "): return None
        token = auth.split(" ")[1]
        with sqlite3.connect(DB_FILE) as conn:
            c = conn.cursor()
            c.execute("SELECT username FROM sessions WHERE token = ?", (token,))
            row = c.fetchone()
            if row: return row[0]
        return None

    def _json_success(self, data):
        body = json.dumps(data).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_cors()
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_cors()
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)

        # ── /quote?symbol=AAPL ────────────────────────────────────────────
        if parsed.path == "/quote":
            params = parse_qs(parsed.query)
            symbol = (params.get("symbol") or params.get("ticker") or [""])[0].upper()
            if not symbol:
                self._json_error(400, "Missing symbol parameter")
                return
            try:
                data = get_stock_data(symbol)
                body = json.dumps(data).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_cors()
                self.end_headers()
                self.wfile.write(body)
            except Exception as e:
                print(f"  Error fetching {symbol}: {e}")
                self._json_error(404, str(e))
            return

        # ── /api/portfolio ───────────────────────────────────────────────
        if parsed.path == "/api/portfolio":
            user = self.get_user_from_auth()
            if not user: return self._json_error(401, "Unauthorized")
            with sqlite3.connect(DB_FILE) as conn:
                c = conn.cursor()
                c.execute("SELECT ticker FROM portfolios WHERE username = ?", (user,))
                tickers = [r[0] for r in c.fetchall()]
            return self._json_success({"tickers": tickers})

        # ── / → serve HTML ────────────────────────────────────────────────
        if parsed.path in ("/", "/index.html") or parsed.path == "":
            try:
                with open(HTML_FILE, "rb") as f:
                    content = f.read()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write(content)
            except FileNotFoundError:
                self._json_error(404, f"HTML no encontrado: {HTML_FILE}")
            return

        self._json_error(404, "Not found")

    def do_POST(self):
        parsed = urlparse(self.path)
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length) if content_length > 0 else b""
        req = {}
        if post_data:
            try: req = json.loads(post_data.decode())
            except: pass

        if parsed.path == "/api/signup":
            username = req.get("username", "").strip()
            password = req.get("password", "")
            if not username or not password: return self._json_error(400, "Faltan datos")
            with sqlite3.connect(DB_FILE) as conn:
                c = conn.cursor()
                try:
                    c.execute("INSERT INTO users (username, password_hash) VALUES (?, ?)", (username, hash_password(password)))
                    conn.commit()
                except sqlite3.IntegrityError:
                    return self._json_error(400, "El usuario ya existe")
            token = str(uuid.uuid4())
            with sqlite3.connect(DB_FILE) as conn:
                conn.cursor().execute("INSERT INTO sessions (token, username) VALUES (?, ?)", (token, username))
                conn.commit()
            return self._json_success({"token": token, "username": username})

        if parsed.path == "/api/login":
            username = req.get("username", "").strip()
            password = req.get("password", "")
            with sqlite3.connect(DB_FILE) as conn:
                c = conn.cursor()
                c.execute("SELECT password_hash FROM users WHERE username = ?", (username,))
                row = c.fetchone()
                if row and row[0] == hash_password(password):
                    token = str(uuid.uuid4())
                    c.execute("INSERT INTO sessions (token, username) VALUES (?, ?)", (token, username))
                    conn.commit()
                    return self._json_success({"token": token, "username": username})
                else:
                    return self._json_error(401, "Credenciales incorrectas")

        if parsed.path == "/api/portfolio":
            user = self.get_user_from_auth()
            if not user: return self._json_error(401, "Unauthorized")
            ticker = req.get("ticker", "").strip().upper()
            if not ticker: return self._json_error(400, "Falta el ticker")
            with sqlite3.connect(DB_FILE) as conn:
                c = conn.cursor()
                try:
                    c.execute("INSERT INTO portfolios (username, ticker) VALUES (?, ?)", (user, ticker))
                    conn.commit()
                except sqlite3.IntegrityError:
                    pass
            return self._json_success({"success": True})

        self._json_error(404, "Not found")

    def do_DELETE(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/portfolio":
            user = self.get_user_from_auth()
            if not user: return self._json_error(401, "Unauthorized")
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length) if content_length > 0 else b""
            req = {}
            if post_data:
                try: req = json.loads(post_data.decode())
                except: pass
            ticker = req.get("ticker", "").strip().upper()
            if not ticker: return self._json_error(400, "Falta el ticker")
            with sqlite3.connect(DB_FILE) as conn:
                c = conn.cursor()
                c.execute("DELETE FROM portfolios WHERE username = ? AND ticker = ?", (user, ticker))
                conn.commit()
            return self._json_success({"success": True})

        self._json_error(404, "Not found")

    def _json_error(self, code, msg):
        body = json.dumps({"error": msg}).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_cors()
        self.end_headers()
        self.wfile.write(body)


if __name__ == "__main__":
    server = HTTPServer(("localhost", PORT), Handler)
    print(f"\n✅  Servidor en http://localhost:{PORT}")
    print(f"   Abrí esa URL en tu navegador")
    print(f"   Ctrl+C para detener\n")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n⛔  Servidor detenido.")
