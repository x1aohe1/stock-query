#!/usr/bin/env python3
"""
股票行情 API 服务 - 基于 AkShare（简化稳定版）
实时行情：腾讯 API
历史数据：AkShare stock_zh_a_daily
"""

from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import urllib.request
import re
import time
from datetime import datetime, timedelta, date

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
                date_param = params.get('date', [''])[0]
                result = get_historical_open(symbol, date_param)
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
    """获取实时行情 - 腾讯 API"""
    if not symbol:
        return {'error': 'Missing symbol'}
    
    try:
        url = f'https://qt.gtimg.cn/q={symbol.lower()}'
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        
        with urllib.request.urlopen(req, timeout=10) as resp:
            content = resp.read().decode('gbk')
        
        match = re.search(r'="([^"]+)"', content)
        if not match:
            return {'error': 'Invalid response'}
        
        elements = match.group(1).split('~')
        if len(elements) < 33:
            return {'error': 'Invalid format'}
        
        # 腾讯返回的 name 已经是正确的中文字符串（GBK 解码后）
        name = elements[1]
        current = float(elements[3]) if elements[3] else 0
        close = float(elements[4]) if elements[4] else 0
        
        return {
            'code': symbol.upper(),
            'name': name,  # 已经是正确的中文
            'current': current,
            'close': close,
            'open': float(elements[5]) if elements[5] else 0,
            'high': float(elements[32]) if elements[32] else 0,
            'low': float(elements[33]) if len(elements) > 33 and elements[33] else 0,
            'change': current - close,
            'changePercent': (current - close) / close * 100 if close > 0 else 0
        }
    except Exception as e:
        return {'error': str(e)}

def get_historical_open(symbol, date_param):
    """获取历史开盘价 - AkShare"""
    import akshare as ak
    
    if not symbol or not date_param:
        return {'error': 'Missing parameters'}
    
    symbol = symbol.upper()
    if not (symbol.startswith('SH') or symbol.startswith('SZ')):
        return {'error': 'Only A-shares supported'}
    
    code = symbol.lower()
    
    # 解析日期
    date_str = date_param.replace('-', '')
    try:
        target = date(int(date_str[:4]), int(date_str[4:6]), int(date_str[6:8]))
        start = (target - timedelta(days=180)).strftime('%Y%m%d')
        end = (target + timedelta(days=30)).strftime('%Y%m%d')
    except:
        return {'error': 'Invalid date'}
    
    # 重试获取数据
    for retry in range(3):
        try:
            df = ak.stock_zh_a_daily(symbol=code, start_date=start, end_date=end)
            if df is None or len(df) == 0:
                time.sleep(2)
                continue
            
            # 查找匹配日期
            matched = df[df['date'] == target]
            
            if len(matched) > 0:
                row = matched.iloc[0]
                return {
                    'open': float(row['open']),
                    'close': float(row['close']),
                    'high': float(row['high']),
                    'low': float(row['low']),
                    'date': date_param,
                    'symbol': symbol
                }
            
            # 找不到返回最近的
            if len(df) > 0:
                row = df.iloc[-1]
                return {
                    'open': float(row['open']),
                    'close': float(row['close']),
                    'date': date_param,
                    'symbol': symbol,
                    'note': f'Using nearest: {row["date"]}'
                }
                
        except Exception as e:
            if retry < 2:
                time.sleep(2)
            else:
                return {'error': str(e)}
    
    return {'error': 'No data'}

if __name__ == '__main__':
    server = HTTPServer(('127.0.0.1', PORT), StockAPIHandler)
    print(f"🚀 API running on http://127.0.0.1:{PORT}")
    server.serve_forever()
