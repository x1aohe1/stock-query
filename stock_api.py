#!/usr/bin/env python3
"""
股票行情 API 服务 - 简单版
使用腾讯 API 作为数据源，提供 UTF-8 编码的 JSON
"""

from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import urllib.request
import urllib.parse
import re

PORT = 8765

class StockAPIHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)
        
        try:
            if parsed.path == '/quote':
                symbol = params.get('symbol', [''])[0].upper()
                result = get_quote(symbol)
                self.send_json(result)
                
            elif parsed.path == '/history':
                symbol = params.get('symbol', [''])[0].upper()
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
    """获取实时行情 - 使用腾讯 API"""
    if not symbol:
        return {'error': 'Missing symbol'}
    
    # 转换为腾讯格式
    code = symbol.lower()
    
    try:
        url = f'https://qt.gtimg.cn/q={code}'
        headers = {'User-Agent': 'Mozilla/5.0'}
        req = urllib.request.Request(url, headers=headers)
        
        with urllib.request.urlopen(req, timeout=10) as resp:
            content = resp.read().decode('gbk')  # 腾讯返回 GBK 编码
            
        # 解析：v_sh600519="1~贵州茅台~600519~1402.00~1399.04~..."
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
    """获取历史开盘价 - 使用腾讯 API"""
    if not symbol or not date:
        return {'error': 'Missing symbol or date'}
    
    code = symbol.lower()
    
    try:
        # 腾讯历史数据 API
        url = f'https://web.ifzq.gtimg.cn/appstock/app/fqkline/get?param={code},day,,,300,qfq'
        headers = {'User-Agent': 'Mozilla/5.0'}
        req = urllib.request.Request(url, headers=headers)
        
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode('utf-8'))
        
        if data.get('code') != 0 or not data.get('data'):
            return {'open': None, 'error': 'No data'}
        
        kline = data['data'].get(code, {}).get('qfqday', [])
        if not kline:
            return {'open': None, 'error': 'No kline data'}
        
        # 查找匹配日期的数据
        target_date = date.replace('-', '')
        for k in kline:
            if k[0] == target_date:
                return {'open': float(k[1]), 'date': date, 'symbol': symbol}
        
        # 找不到返回最近的
        if kline:
            return {'open': float(kline[0][1]), 'date': date, 'symbol': symbol, 'note': 'Using nearest date'}
        
        return {'open': None, 'error': 'Date not found'}
        
    except Exception as e:
        return {'error': str(e)}

if __name__ == '__main__':
    server = HTTPServer(('127.0.0.1', PORT), StockAPIHandler)
    print(f"🚀 Stock API Server running on http://127.0.0.1:{PORT}")
    print(f"   Endpoints:")
    print(f"   - GET /quote?symbol=SH600519  实时行情")
    print(f"   - GET /history?symbol=SH600519&date=2025-01-15  历史开盘价")
    print(f"   - GET /health  健康检查")
    server.serve_forever()
