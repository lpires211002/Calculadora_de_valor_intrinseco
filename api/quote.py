import json
from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import os
os.environ["YFINANCE_CACHE_DIR"] = "/tmp/yfinance_cache"
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

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)
        symbol = (params.get("symbol") or params.get("ticker") or [""])[0].upper()

        if not symbol:
            self.send_response(400)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps({"error": "Missing symbol parameter"}).encode())
            return

        try:
            data = get_stock_data(symbol)
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(data).encode())
        except Exception as e:
            self.send_response(404)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode())
