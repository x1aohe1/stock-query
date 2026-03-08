#!/usr/bin/env python3
"""
数据源模块 - 统一管理行情和历史数据获取
方便后续替换不同的数据源
"""

from typing import Optional, Dict
from datetime import datetime, timedelta
import time
import pandas as pd
import subprocess
import sys
import os

# ==================== 实时行情数据源 ====================

class QuoteDataSource:
    """实时行情数据源接口"""
    
    def get_quote(self, code: str) -> Optional[Dict]:
        """获取实时行情"""
        raise NotImplementedError

class TencentQuoteDataSource(QuoteDataSource):
    """腾讯实时行情数据源"""
    
    def get_quote(self, code: str) -> Optional[Dict]:
        """从腾讯 API 获取实时行情"""
        import urllib.request
        import re
        
        try:
            url = f'https://qt.gtimg.cn/q={code.lower()}'
            headers = {'User-Agent': 'Mozilla/5.0'}
            req = urllib.request.Request(url, headers=headers)
            
            with urllib.request.urlopen(req, timeout=10) as resp:
                content = resp.read().decode('gbk')
            
            match = re.search(r'="([^"]+)"', content)
            if not match:
                return None
            
            elements = match.group(1).split('~')
            if len(elements) < 50:
                return None
            
            name = elements[1]
            current = float(elements[3]) if elements[3] else 0
            close = float(elements[4]) if elements[4] else 0
            open_price = float(elements[5]) if elements[5] else 0
            high = float(elements[32]) if elements[32] else 0
            low = float(elements[33]) if len(elements) > 33 and elements[33] else 0
            change = current - close
            change_percent = (change / close * 100) if close > 0 else 0
            
            return {
                'code': code,
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
            print(f"获取实时行情失败 {code}: {e}")
            return None

# 全局实例
quote_source = TencentQuoteDataSource()

def get_realtime_quote(code: str) -> Optional[Dict]:
    """获取实时行情（统一入口）"""
    return quote_source.get_quote(code)

# ==================== 历史数据源 ====================

class HistoryDataSource:
    """历史数据源接口"""
    
    def get_history(self, code: str, date: str) -> Optional[Dict]:
        """
        获取历史数据
        
        Args:
            code: 股票代码（如 SZ002716）
            date: 日期（如 2026-01-23）
        
        Returns:
            {
                'date': '2026-01-23',
                'open': 16.0,
                'close': 16.44,
                'high': 16.45,
                'low': 15.55,
                'note': '可选的说明信息'
            }
        """
        raise NotImplementedError

class GetStockHistoryDataSource(HistoryDataSource):
    """
    使用 get_stock.py 脚本获取历史数据
    
    使用方式：
        /home/x1aohe1/.openclaw/workspace/ak_env/bin/python get_stock.py 002716 -m a -d 2026-01-23
    """
    
    def __init__(self):
        # get_stock.py 脚本路径
        self.script_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            'get_stock.py'
        )
        # Python 解释器路径
        self.python_path = '/home/x1aohe1/.openclaw/workspace/ak_env/bin/python'
    
    def _format_code(self, code: str) -> tuple:
        """
        格式化股票代码，返回 (symbol, market)
        
        SZ002716 -> ('002716', 'a')
        HK00700 -> ('00700', 'hk')
        USNVDA -> ('NVDA', 'us')
        """
        code = code.upper()
        if code.startswith('SZ') or code.startswith('SH'):
            return (code[2:], 'a')
        elif code.startswith('HK'):
            return (code[2:], 'hk')
        elif code.startswith('US'):
            return (code[2:], 'us')
        return (code, 'a')
    
    def get_history(self, code: str, date: str) -> Optional[Dict]:
        """从 get_stock.py 获取历史数据"""
        try:
            symbol, market = self._format_code(code)
            
            print(f"获取历史数据 {code} {date}...")
            print(f"   调用：{self.python_path} {self.script_path} {symbol} -m {market} -d {date}")
            
            # 调用脚本
            result = subprocess.run(
                [self.python_path, self.script_path, symbol, '-m', market, '-d', date],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode != 0:
                print(f"   ❌ 脚本执行失败：{result.stderr}")
                return None
            
            output = result.stdout
            print(f"   脚本输出：{output[:500]}...")
            
            # 解析输出
            # 格式 1: 单日详情 - "开盘： $193.03"
            # 格式 2: 表格 - "2026-01-23        16.00      16.45      15.55      16.44"
            lines = output.split('\n')
            open_price = None
            close_price = None
            high_price = None
            low_price = None
            found_date = None
            
            # 先尝试解析单日详情格式
            for line in lines:
                line = line.strip()
                if '开盘：' in line:
                    parts = line.split('开盘：')
                    if len(parts) > 1:
                        price_str = parts[1].strip().replace('$', '').replace('¥', '').replace('HK$', '').replace(',', '')
                        try:
                            open_price = float(price_str)
                        except:
                            pass
                elif '收盘：' in line:
                    parts = line.split('收盘：')
                    if len(parts) > 1:
                        price_str = parts[1].strip().replace('$', '').replace('¥', '').replace('HK$', '').replace(',', '')
                        try:
                            close_price = float(price_str)
                        except:
                            pass
                elif '最高：' in line:
                    parts = line.split('最高：')
                    if len(parts) > 1:
                        price_str = parts[1].strip().replace('$', '').replace('¥', '').replace('HK$', '').replace(',', '')
                        try:
                            high_price = float(price_str)
                        except:
                            pass
                elif '最低：' in line:
                    parts = line.split('最低：')
                    if len(parts) > 1:
                        price_str = parts[1].strip().replace('$', '').replace('¥', '').replace('HK$', '').replace(',', '')
                        try:
                            low_price = float(price_str)
                        except:
                            pass
                elif '日期：' in line:
                    parts = line.split('日期：')
                    if len(parts) > 1:
                        found_date = parts[1].strip()
            
            # 如果是表格格式，查找目标日期的行
            if open_price is None:
                for line in lines:
                    line = line.strip()
                    # 匹配日期行：2026-01-23        16.00      16.45      15.55      16.44
                    if line.startswith(date):
                        parts = line.split()
                        if len(parts) >= 5:
                            try:
                                found_date = parts[0]
                                open_price = float(parts[1].replace(',', ''))
                                high_price = float(parts[2].replace(',', ''))
                                low_price = float(parts[3].replace(',', ''))
                                close_price = float(parts[4].replace(',', ''))
                                print(f"   从表格解析：开盘={open_price}")
                            except Exception as e:
                                print(f"   表格解析失败：{e}")
            
            if open_price is not None:
                print(f"   ✅ 获取成功：开盘={open_price}")
                return {
                    'date': found_date or date,
                    'open': open_price,
                    'close': close_price,
                    'high': high_price,
                    'low': low_price,
                    'note': f'使用 {found_date or date} 的开盘价'
                }
            else:
                print(f"   ⚠️ 未找到开盘价")
                return None
                
        except subprocess.TimeoutExpired:
            print(f"   ❌ 脚本执行超时")
            return None
        except Exception as e:
            print(f"   ❌ 获取历史数据失败：{e}")
            return None

class AkShareHistoryDataSource(HistoryDataSource):
    """AkShare 历史数据源（备用）"""
    
    def __init__(self, max_retries: int = 3):
        self.max_retries = max_retries
        self.ak = None
    
    def _load_akshare(self):
        """延迟加载 AkShare"""
        if self.ak is None:
            try:
                import akshare as ak_module
                self.ak = ak_module
                print("✅ AkShare 已加载")
            except Exception as e:
                print(f"❌ AkShare 加载失败：{e}")
                return False
        return True
    
    def get_history(self, code: str, date: str) -> Optional[Dict]:
        """从 AkShare 获取历史数据"""
        if not self._load_akshare():
            return None
        
        # 检测市场
        market = self._detect_market(code)
        
        # 解析日期
        try:
            target_date = datetime.strptime(date, '%Y-%m-%d')
            start_date = (target_date - timedelta(days=60)).strftime('%Y%m%d')
            end_date = (target_date + timedelta(days=30)).strftime('%Y%m%d')
            target_date_str = target_date.strftime('%Y-%m-%d')
        except Exception as e:
            print(f"日期解析失败 {date}: {e}")
            return None
        
        # 重试机制
        for retry in range(self.max_retries):
            try:
                print(f"获取历史数据 {code} {date} (尝试 {retry+1}/{self.max_retries})...")
                
                if market == 'a':
                    result = self._get_a_share_history(code, target_date_str, start_date, end_date)
                elif market == 'hk':
                    result = self._get_hk_share_history(code, target_date_str)
                elif market == 'us':
                    result = self._get_us_share_history(code, target_date_str)
                else:
                    return None
                
                if result:
                    return result
                
                if retry < self.max_retries - 1:
                    print(f"未找到数据，{2 ** (retry + 1)}秒后重试...")
                    time.sleep(2 ** (retry + 1))
                    
            except Exception as e:
                print(f"获取历史数据失败 {code} {date}: {e}")
                if retry < self.max_retries - 1:
                    print(f"{2 ** (retry + 1)}秒后重试...")
                    time.sleep(2 ** (retry + 1))
                else:
                    return None
        
        return None
    
    def _detect_market(self, code: str) -> str:
        """检测市场类型"""
        code = code.upper()
        if code.startswith('HK'):
            return 'hk'
        if code.startswith('US'):
            return 'us'
        if code.startswith('SH') or code.startswith('SZ'):
            return 'a'
        return 'a'
    
    def _get_a_share_history(self, code: str, target_date_str: str, start_date: str, end_date: str) -> Optional[Dict]:
        """获取 A 股历史数据"""
        df = self.ak.stock_zh_a_daily(symbol=code.lower(), start_date=start_date, end_date=end_date)
        
        if len(df) == 0:
            return None
        
        print(f"   获取到 {len(df)} 条记录，日期范围：{df.iloc[0]['date']} 到 {df.iloc[-1]['date']}")
        
        # 精确匹配
        matched = df[df['date'] == target_date_str]
        if len(matched) > 0:
            row = matched.iloc[0]
            print(f"   ✅ 找到目标日期：{target_date_str}, 开盘={row['open']}")
            return {
                'date': target_date_str,
                'open': float(row['open']),
                'close': float(row['close']),
                'high': float(row['high']),
                'low': float(row['low'])
            }
        
        # 找最接近的交易日
        print(f"   ⚠️ 未找到 {target_date_str}，查找最接近的交易日...")
        df['date_obj'] = pd.to_datetime(df['date'])
        target_dt = pd.to_datetime(target_date_str)
        df['diff'] = (df['date_obj'] - target_dt).abs()
        closest = df.loc[df['diff'].idxmin()]
        print(f"   使用最接近的日期：{closest['date']}, 开盘={closest['open']}")
        
        return {
            'date': target_date_str,
            'open': float(closest['open']),
            'note': f'原日期 {target_date_str} 非交易日，使用 {closest["date"]} 的开盘价'
        }
    
    def _get_hk_share_history(self, code: str, target_date_str: str) -> Optional[Dict]:
        """获取港股历史数据"""
        symbol = code[2:].lower()  # 去掉 HK 前缀
        print(f"   获取港股历史数据：{symbol}...")
        
        df = self.ak.stock_hk_daily(symbol=symbol)
        if len(df) == 0 or 'date' not in df.columns:
            print(f"   ⚠️ 港股数据获取失败或无 date 列")
            return None
        
        df['date_obj'] = pd.to_datetime(df['date'])
        target_dt = pd.to_datetime(target_date_str)
        df['diff'] = (df['date_obj'] - target_dt).abs()
        closest = df.loc[df['diff'].idxmin()]
        print(f"   使用日期：{closest['date']}, 开盘={closest['open']}")
        
        return {
            'date': target_date_str,
            'open': float(closest['open']),
            'note': f'使用 {closest["date"]} 的开盘价'
        }
    
    def _get_us_share_history(self, code: str, target_date_str: str) -> Optional[Dict]:
        """获取美股历史数据"""
        symbol = code[2:].upper()  # 去掉 US 前缀
        print(f"   获取美股历史数据：{symbol}...")
        
        df = self.ak.stock_us_daily(symbol=symbol)
        if len(df) == 0:
            return None
        
        df['date_obj'] = pd.to_datetime(df['date'])
        target_dt = pd.to_datetime(target_date_str)
        df['diff'] = (df['date_obj'] - target_dt).abs()
        closest = df.loc[df['diff'].idxmin()]
        print(f"   使用日期：{closest['date']}, 开盘={closest['open']}")
        
        return {
            'date': target_date_str,
            'open': float(closest['open']),
            'note': f'使用 {closest["date"]} 的开盘价'
        }

# ==================== 配置数据源 ====================

# 当前使用 get_stock.py 作为历史数据源
# 如果需要切换回 AkShare，取消下面这行的注释：
# history_source = AkShareHistoryDataSource(max_retries=3)

# 使用 get_stock.py 脚本
history_source = GetStockHistoryDataSource()

def get_historical_data(code: str, date: str) -> Optional[Dict]:
    """获取历史数据（统一入口）"""
    return history_source.get_history(code, date)

# ==================== 替换数据源说明 ====================
"""
当有新的历史数据 API 时，只需：

1. 创建新的数据源类，继承 HistoryDataSource
2. 实现 get_history() 方法
3. 替换全局实例：
   
   # 原来：
   history_source = GetStockHistoryDataSource()
   
   # 改为：
   history_source = NewAPIDataSource(api_key='xxx')

4. 重启后端服务

无需修改 main.py 中的任何代码！
"""
