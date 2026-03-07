#!/usr/bin/env python3
"""
股票行情 API 服务 - 基于 AkShare
提供 HTTP API 供网页调用
"""

from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import urllib.parse
import sys
import os

# 添加 akshare 到路径
sys.path.insert(0, '/home/x1aohe1/.openclaw/workspace')
os.environ['PATH'] = '/home/x1aohe1/.openclaw/workspace/ak_env/bin:' + os.environ['PATH']

import akshare as ak

class StockAPIHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)
        
        try:
            if parsed.path == '/quote':
                # 获取实时行情
                symbol = params.get('symbol', [''])[0]
                result = get_quote(symbol)
                self.send_json(result)
                
            elif parsed.path == '/history':
                # 获取历史数据
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
        self.send_header('Content-Type', 'application/json')
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
    """获取实时行情"""
    symbol = symbol.upper()
    
    # 提取市场前缀
    if symbol.startswith('SH') or symbol.startswith('SZ'):
        code = symbol[2:]
        market = symbol[:2].lower()
    elif symbol.startswith('HK'):
        # 港股
        code = symbol[2:].lstrip('0')
        return get_hk_quote(code)
    elif symbol.startswith('US'):
        # 美股
        code = symbol[2:]
        return get_us_quote(code)
    else:
        return {'error': 'Invalid symbol'}
    
    try:
        # A 股实时行情
        df = ak.stock_zh_a_spot_em()
        stock_data = df[df['代码'] == code]
        
        if len(stock_data) == 0:
            return {'error': 'Stock not found', 'code': symbol}
        
        row = stock_data.iloc[0]
        current = float(row['最新价'])
        close = float(row['昨收'])
        change = current - close
        change_percent = (change / close * 100) if close > 0 else 0
        
        return {
            'code': symbol,
            'name': row['名称'],
            'current': current,
            'close': close,
            'open': float(row['今开']),
            'high': float(row['最高']),
            'low': float(row['最低']),
            'change': change,
            'changePercent': change_percent
        }
    except Exception as e:
        return {'error': str(e)}

def get_hk_quote(code):
    """获取港股行情"""
    try:
        df = ak.stock_hk_daily_em(symbol=f'HK{code}')
        if len(df) == 0:
            return {'error': 'Stock not found'}
        row = df.iloc[-1]
        return {
            'code': f'HK{code}',
            'name': row.get('名称', ''),
            'current': float(row['收盘']),
            'close': float(row['昨收']) if '昨收' in row else float(row['收盘']),
            'change': 0,
            'changePercent': 0
        }
    except Exception as e:
        return {'error': str(e)}

def get_us_quote(code):
    """获取美股行情"""
    try:
        df = ak.stock_us_daily_em(symbol=code)
        if len(df) == 0:
            return {'error': 'Stock not found'}
        row = df.iloc[-1]
        return {
            'code': f'US{code}',
            'name': row.get('名称', ''),
            'current': float(row['收盘']),
            'close': float(row['昨收']) if '昨收' in row else float(row['收盘']),
            'change': 0,
            'changePercent': 0
        }
    except Exception as e:
        return {'error': str(e)}

def get_historical_open(symbol, date):
    """获取历史开盘价"""
    if not symbol or not date:
        return {'error': 'Missing symbol or date'}
    
    symbol = symbol.upper()
    
    # 提取代码
    if symbol.startswith('SH') or symbol.startswith('SZ'):
        code = symbol.lower()
    else:
        return {'error': 'Only A-shares supported for history'}
    
    try:
        # 转换日期格式
        date_str = date.replace('-', '')
        start_date = date_str
        end_date = date_str
        
        # 获取历史数据
        df = ak.stock_zh_a_daily(symbol=code, start_date=start_date, end_date=end_date)
        
        if len(df) == 0:
            return {'open': None, 'error': 'No data for this date'}
        
        open_price = float(df.iloc[0]['open'])
        return {'open': open_price, 'date': date, 'symbol': symbol}
        
    except Exception as e:
        return {'error': str(e)}

if __name__ == '__main__':
    port = 8765
    server = HTTPServer(('127.0.0.1', port), StockAPIHandler)
    print(f"🚀 Stock API Server running on http://127.0.0.1:{port}")
    print(f"   Endpoints:")
    print(f"   - GET /quote?symbol=SH600519  实时行情")
    print(f"   - GET /history?symbol=SH600519&date=2025-01-15  历史开盘价")
    print(f"   - GET /health  健康检查")
    server.serve_forever()
