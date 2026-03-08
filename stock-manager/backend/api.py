"""
Stock Quote API - 股票行情查询接口
支持 A 股、港股、美股
"""

import os
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
import akshare as ak
import pandas as pd

# 设置代理环境变量
os.environ['HTTP_PROXY'] = 'http://172.20.128.1:26001'
os.environ['HTTPS_PROXY'] = 'http://172.20.128.1:26001'

app = FastAPI(
    title="Stock Quote API",
    description="股票行情查询接口 - 支持 A 股、港股、美股",
    version="1.0.0"
)

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class StockQuote(BaseModel):
    """股票行情数据模型"""
    symbol: str
    date: str
    market: str
    name: Optional[str] = None
    open: Optional[float] = None
    close: Optional[float] = None
    high: Optional[float] = None
    low: Optional[float] = None
    volume: Optional[float] = None
    amount: Optional[float] = None
    change: Optional[float] = None
    change_percent: Optional[float] = None
    turnover: Optional[float] = None
    pe: Optional[float] = None
    pb: Optional[float] = None
    timestamp: str


def detect_market(symbol: str) -> str:
    """根据股票代码识别市场"""
    symbol = symbol.upper()
    
    # A 股：6 位数字 + .sz/.sh 或纯 6 位数字
    if symbol.endswith('.SZ') or symbol.endswith('.SH'):
        return 'A'
    if symbol.isdigit() and len(symbol) in [5, 6]:
        return 'A'
    
    # 港股：数字 + .HK
    if symbol.endswith('.HK'):
        return 'HK'
    
    # 美股：字母代码
    if symbol.replace('.', '').replace('-', '').isalpha():
        return 'US'
    
    # 默认尝试 A 股
    return 'A'


def get_a_stock_quote(symbol: str, date: str) -> dict:
    """获取 A 股行情数据"""
    # 标准化股票代码
    symbol = symbol.upper()
    prefix = ''
    if symbol.startswith('6'):
        prefix = 'sh'
    else:
        prefix = 'sz'
    
    if symbol.endswith('.SZ'):
        symbol = 'sz' + symbol[:-3]
    elif symbol.endswith('.SH'):
        symbol = 'sh' + symbol[:-3]
    elif symbol.isdigit():
        symbol = prefix + symbol
    
    # 获取历史行情 - 使用 stock_zh_a_daily 接口
    try:
        df = ak.stock_zh_a_daily(symbol=symbol)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取 A 股数据失败：{str(e)}")
    
    if df is None or len(df) == 0:
        raise HTTPException(status_code=404, detail=f"未找到股票 {symbol} 的数据")
    
    # 筛选指定日期
    df['date'] = pd.to_datetime(df['date']).dt.strftime('%Y-%m-%d')
    row_df = df[df['date'] == date]
    
    if len(row_df) == 0:
        raise HTTPException(status_code=404, detail=f"未找到股票 {symbol} 在 {date} 的数据")
    
    row = row_df.iloc[0]
    
    return {
        "symbol": symbol,
        "date": date,
        "market": "A",
        "name": "",
        "open": float(row.get('open', 0)) if row.get('open') else None,
        "close": float(row.get('close', 0)) if row.get('close') else None,
        "high": float(row.get('high', 0)) if row.get('high') else None,
        "low": float(row.get('low', 0)) if row.get('low') else None,
        "volume": float(row.get('volume', 0)) if row.get('volume') else None,
        "amount": float(row.get('amount', 0)) if row.get('amount') else None,
        "turnover": float(row.get('turnover', 0)) if row.get('turnover') else None,
        "timestamp": datetime.now().isoformat()
    }


def get_hk_stock_quote(symbol: str, date: str) -> dict:
    """获取港股行情数据"""
    import traceback
    symbol = symbol.upper()
    if symbol.endswith('.HK'):
        symbol = symbol[:-3]
    
    try:
        df = ak.stock_hk_daily(symbol=symbol)
    except Exception as e:
        print(f"港股数据获取错误：{e}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"获取港股数据失败：{str(e)}")
    
    if df is None or len(df) == 0:
        raise HTTPException(status_code=404, detail=f"未找到港股 {symbol} 的数据")
    
    try:
        # 筛选指定日期
        df['date'] = pd.to_datetime(df['date']).dt.strftime('%Y-%m-%d')
        row_df = df[df['date'] == date]
        
        if len(row_df) == 0:
            raise HTTPException(status_code=404, detail=f"未找到港股 {symbol} 在 {date} 的数据")
        
        row = row_df.iloc[0]
        
        return {
            "symbol": f"{symbol}.HK",
            "date": date,
            "market": "HK",
            "name": "",
            "open": float(row.get('open', 0)) if pd.notna(row.get('open')) else None,
            "close": float(row.get('close', 0)) if pd.notna(row.get('close')) else None,
            "high": float(row.get('high', 0)) if pd.notna(row.get('high')) else None,
            "low": float(row.get('low', 0)) if pd.notna(row.get('low')) else None,
            "volume": float(row.get('volume', 0)) if pd.notna(row.get('volume')) else None,
            "amount": None,
            "timestamp": datetime.now().isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"港股数据处理错误：{e}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"处理港股数据失败：{str(e)}")


def get_us_stock_quote(symbol: str, date: str) -> dict:
    """获取美股行情数据"""
    symbol = symbol.upper()
    
    try:
        df = ak.stock_us_daily(symbol=symbol)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取美股数据失败：{str(e)}")
    
    if df is None or len(df) == 0:
        raise HTTPException(status_code=404, detail=f"未找到美股 {symbol} 的数据")
    
    # 筛选指定日期
    df['date'] = pd.to_datetime(df['date']).dt.strftime('%Y-%m-%d')
    row_df = df[df['date'] == date]
    
    if len(row_df) == 0:
        raise HTTPException(status_code=404, detail=f"未找到美股 {symbol} 在 {date} 的数据")
    
    row = row_df.iloc[0]
    
    return {
        "symbol": symbol,
        "date": date,
        "market": "US",
        "name": "",
        "open": float(row.get('open', 0)) if row.get('open') else None,
        "close": float(row.get('close', 0)) if row.get('close') else None,
        "high": float(row.get('high', 0)) if row.get('high') else None,
        "low": float(row.get('low', 0)) if row.get('low') else None,
        "volume": float(row.get('volume', 0)) if row.get('volume') else None,
        "amount": None,
        "timestamp": datetime.now().isoformat()
    }


@app.get("/")
def root():
    """API 根路径"""
    return {
        "service": "Stock Quote API",
        "version": "1.0.0",
        "docs": "/docs",
        "endpoints": {
            "GET /stock/quote": "获取股票历史行情"
        }
    }


@app.get("/stock/quote", response_model=StockQuote)
def get_stock_quote(
    symbol: str = Query(..., description="股票代码，如：000001.sz, AAPL, 0700.HK"),
    date: str = Query(..., description="日期，格式：YYYY-MM-DD")
):
    """
    获取股票历史行情数据
    
    - **symbol**: 股票代码
      - A 股：000001.sz, 600519.sh 或纯数字
      - 港股：0700.HK, TCE.HK
      - 美股：AAPL, GOOGL, MSFT
    - **date**: 交易日期，格式 YYYY-MM-DD
    
    返回：开盘价、收盘价、最高价、最低价、成交量等
    """
    # 验证日期格式
    try:
        datetime.strptime(date, '%Y-%m-%d')
    except ValueError:
        raise HTTPException(status_code=400, detail="日期格式错误，请使用 YYYY-MM-DD 格式")
    
    # 识别市场
    market = detect_market(symbol)
    
    # 根据市场获取数据
    try:
        if market == 'A':
            return get_a_stock_quote(symbol, date)
        elif market == 'HK':
            return get_hk_stock_quote(symbol, date)
        elif market == 'US':
            return get_us_stock_quote(symbol, date)
        else:
            raise HTTPException(status_code=400, detail="无法识别股票市场类型")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取数据失败：{str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)
