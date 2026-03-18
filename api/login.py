import json
from http.server import BaseHTTPRequestHandler
import sqlite3
import uuid
import hashlib

DB_FILE = "/tmp/database.db"

def init_db():
    with sqlite3.connect(DB_FILE) as conn:
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password_hash TEXT)''')
        c.execute('''CREATE TABLE IF NOT EXISTS sessions (token TEXT PRIMARY KEY, username TEXT)''')
        c.execute('''CREATE TABLE IF NOT EXISTS portfolios (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT, ticker TEXT, UNIQUE(username, ticker))''')
        conn.commit()

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

class handler(BaseHTTPRequestHandler):
    def send_cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

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

    def do_POST(self):
        init_db()
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length) if content_length > 0 else b""
        req = {}
        if post_data:
            try: req = json.loads(post_data.decode())
            except: pass

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
                return self._json_response(200, {"token": token, "username": username})
            else:
                return self._json_response(401, {"error": "Credenciales incorrectas"})
