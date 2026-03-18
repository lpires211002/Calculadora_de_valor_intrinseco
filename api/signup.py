import json
import os
from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse
import psycopg2
import uuid
import hashlib
from dotenv import load_dotenv

load_dotenv()

def get_db():
    return psycopg2.connect(os.environ.get("POSTGRES_URL_NON_POOLING", os.environ.get("POSTGRES_URL")))

def init_db():
    with get_db() as conn:
        with conn.cursor() as c:
            c.execute('''CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password_hash TEXT)''')
            c.execute('''CREATE TABLE IF NOT EXISTS sessions (token TEXT PRIMARY KEY, username TEXT)''')
            c.execute('''CREATE TABLE IF NOT EXISTS portfolios (id SERIAL PRIMARY KEY, username TEXT, ticker TEXT, UNIQUE(username, ticker))''')
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
        if not username or not password:
            return self._json_response(400, {"error": "Faltan datos"})
            
        with get_db() as conn:
            with conn.cursor() as c:
                try:
                    c.execute("INSERT INTO users (username, password_hash) VALUES (%s, %s)", (username, hash_password(password)))
                    conn.commit()
                except psycopg2.IntegrityError:
                    return self._json_response(400, {"error": "El usuario ya existe"})
                
        token = str(uuid.uuid4())
        with get_db() as conn:
            with conn.cursor() as c:
                c.execute("INSERT INTO sessions (token, username) VALUES (%s, %s)", (token, username))
                conn.commit()
            
        return self._json_response(200, {"token": token, "username": username})
