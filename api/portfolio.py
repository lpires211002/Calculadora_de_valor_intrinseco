import json
from http.server import BaseHTTPRequestHandler
import sqlite3

DB_FILE = "/tmp/database.db"

def init_db():
    with sqlite3.connect(DB_FILE) as conn:
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password_hash TEXT)''')
        c.execute('''CREATE TABLE IF NOT EXISTS sessions (token TEXT PRIMARY KEY, username TEXT)''')
        c.execute('''CREATE TABLE IF NOT EXISTS portfolios (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT, ticker TEXT, UNIQUE(username, ticker))''')
        conn.commit()

class handler(BaseHTTPRequestHandler):
    def send_cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_cors()
        self.end_headers()

    def _json_response(self, code, data):
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_cors()
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

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

    def do_GET(self):
        init_db()
        user = self.get_user_from_auth()
        if not user: return self._json_response(401, {"error": "Unauthorized"})
        
        with sqlite3.connect(DB_FILE) as conn:
            c = conn.cursor()
            c.execute("SELECT ticker FROM portfolios WHERE username = ?", (user,))
            tickers = [r[0] for r in c.fetchall()]
        return self._json_response(200, {"tickers": tickers})

    def do_POST(self):
        init_db()
        user = self.get_user_from_auth()
        if not user: return self._json_response(401, {"error": "Unauthorized"})
        
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length) if content_length > 0 else b""
        req = {}
        if post_data:
            try: req = json.loads(post_data.decode())
            except: pass
            
        ticker = req.get("ticker", "").strip().upper()
        if not ticker: return self._json_response(400, {"error": "Falta el ticker"})
        
        with sqlite3.connect(DB_FILE) as conn:
            c = conn.cursor()
            try:
                c.execute("INSERT INTO portfolios (username, ticker) VALUES (?, ?)", (user, ticker))
                conn.commit()
            except sqlite3.IntegrityError:
                pass
        return self._json_response(200, {"success": True})

    def do_DELETE(self):
        init_db()
        user = self.get_user_from_auth()
        if not user: return self._json_response(401, {"error": "Unauthorized"})
        
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length) if content_length > 0 else b""
        req = {}
        if post_data:
            try: req = json.loads(post_data.decode())
            except: pass
            
        ticker = req.get("ticker", "").strip().upper()
        if not ticker: return self._json_response(400, {"error": "Falta el ticker"})
        
        with sqlite3.connect(DB_FILE) as conn:
            c = conn.cursor()
            c.execute("DELETE FROM portfolios WHERE username = ? AND ticker = ?", (user, ticker))
            conn.commit()
        return self._json_response(200, {"success": True})
