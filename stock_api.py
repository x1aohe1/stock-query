#!/usr/bin/env python3
"""
股票行情 API 服务 - 混合方案
实时行情：腾讯 API（快速稳定）
历史数据：AkShare（可靠）
"""

from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import urllib.request
import urllib.parse
import re
import sys
import os

sys.path.insert(0, '/home/x1aohe1/.openclaw/workspace')
import akshare as ak

PORT = 8765

class StockAPIHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)
        
        try:
            if parsed.path == '/quote':
                symbol = params.get('symbol', [''])[0]
                result = get_quote(symbol)
                self.send_json(result)
                
            elif parsed.path == '/history':
                symbol = params.get('symbol', [''])[0]
                date = params.get('date', [''])[0]
                result = get_historical_open(symbol, date)
                self.send_json(result)
                
            elif parsed.path == '/health':
                self.send_json({'status': 'ok'})
                
            else:
                self.send_json({'error': 'Not found'}, 404)
                
        except Exception as e:
            self.send_json({'error': str(e)}, 500)
    
    def send_json(self, data, status=200):
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode('utf-8'))
    
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
    
    def log_message(self, format, *args):
        print(f"[API] {args[0]}")

def get_quote(symbol):
    """获取实时行情 - 使用腾讯 API（快速稳定）"""
    if not symbol:
        return {'error': 'Missing symbol'}
    
    symbol = symbol.upper()
    code = symbol.lower()
    
    try:
        url = f'https://qt.gtimg.cn/q={code}'
        headers = {'User-Agent': 'Mozilla/5.0'}
        req = urllib.request.Request(url, headers=headers)
        
        with urllib.request.urlopen(req, timeout=10) as resp:
            content = resp.read().decode('gbk')
        
        match = re.search(r'="([^"]+)"', content)
        if not match:
            return {'error': 'Invalid response', 'code': symbol}
        
        elements = match.group(1).split('~')
        if len(elements) < 50:
            return {'error': 'Invalid data format', 'code': symbol}
        
        name = elements[1]
        current = float(elements[3]) if elements[3] else 0
        close = float(elements[4]) if elements[4] else 0
        open_price = float(elements[5]) if elements[5] else 0
        high = float(elements[32]) if elements[32] else 0
        low = float(elements[33]) if elements[33] else 0
        
        change = current - close
        change_percent = (change / close * 100) if close > 0 else 0
        
        return {
            'code': symbol,
            'name': name,
            'current': current,
            'close': close,
            'open': open_price,
            'high': high,
            'low': low,
            'change': change,
            'changePercent': change_percent
        }
        
    except Exception as e:
        return {'error': str(e)}

def get_historical_open(symbol, date):
    """获取历史开盘价 - 使用 AkShare（可靠）"""
    if not symbol or not date:
        return {'error': 'Missing symbol or date'}
    
    symbol = symbol.upper()
    
    # 只支持 A 股
    if not (symbol.startswith('SH') or symbol.startswith('SZ')):
        return {'error': 'Only A-shares supported for history', 'symbol': symbol}
    
    try:
        # 转换日期格式
        date_str = date.replace('-', '')
        
        from datetime import datetime, timedelta
        target_date = datetime.strptime(date_str, '%Y%m%d')
        start_date = (target_date - timedelta(days=30)).strftime('%Y%m%d')
        end_date = (target_date + timedelta(days=30)).strftime('%Y%m%d')
        
        # 获取日 K 线数据
        code = symbol.lower()
        df = ak.stock_zh_a_daily(symbol=code, start_date=start_date, end_date=end_date)
        
        if len(df) == 0:
            return {'open': None, 'error': 'No data for this period'}
        
        # 查找匹配日期的数据
        target_date_str = target_date.strftime('%Y-%m-%d')
        matched = df[df['date'] == target_date_str]
        
        if len(matched) > 0:
            open_price = float(matched.iloc[0]['open'])
            return {'open': open_price, 'date': date, 'symbol': symbol}
        
        # 找不到精确匹配，返回最近的
        open_price = float(df.iloc[0]['open'])
        return {'open': open_price, 'date': date, 'symbol': symbol, 'note': 'Using nearest date'}
        
    except Exception as e:
        return {'error': str(e)}

if __name__ == '__main__':
    server = HTTPServer(('127.0.0.1', PORT), StockAPIHandler)
    print(f"🚀 Stock API Server running on http://127.0.0.1:{PORT}")
    print(f"   Data sources:")
    print(f"   - Real-time quote: Tencent API (fast & stable)")
    print(f"   - Historical data: AkShare (reliable)")
    print(f"   Endpoints:")
    print(f"   - GET /quote?symbol=SH600519  实时行情")
    print(f"   - GET /history?symbol=SH600519&date=2025-01-15  历史开盘价")
    print(f"   - GET /health  健康检查")
    server.serve_forever()
