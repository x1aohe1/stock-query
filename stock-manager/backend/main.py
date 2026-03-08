#!/usr/bin/env python3
"""
股票管理工具 - 后端服务
混合方案：实时行情用腾讯 API，历史数据用 AkShare（可替换）
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import json
import os
import subprocess
from datetime import datetime

# 导入数据源模块（统一管理行情和历史数据）
from data_sources import get_realtime_quote, get_historical_data

app = FastAPI(title="股票管理工具", version="1.0.0")

# 启用 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 数据文件路径
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_FILE = os.path.join(BASE_DIR, "stock-data.json")
CONFIG_FILE = os.path.join(BASE_DIR, "config.json")

# ==================== 数据模型 ====================

class Buyer(BaseModel):
    name: str
    price: float = 0
    date: str = ""
    calculatedPrice: float = 0

class Stock(BaseModel):
    code: str
    name: str
    market: str
    watchPrice: float = 0
    watchDate: str = ""
    recommender: str = ""
    buyers: List[Buyer] = []

class StockInput(BaseModel):
    code: str
    name: Optional[str] = None
    market: Optional[str] = None
    watchPrice: Optional[float] = None
    watchDate: Optional[str] = None
    recommender: Optional[str] = None
    buyers: Optional[List[Buyer]] = None

class ApiResponse(BaseModel):
    success: bool
    message: str
    data: Optional[Any] = None

# ==================== 辅助函数 ====================

def load_data() -> List[Dict]:
    """加载股票数据"""
    if not os.path.exists(DATA_FILE):
        return []
    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_data(data: List[Dict]):
    """保存股票数据"""
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def load_config() -> Dict:
    """加载配置"""
    if not os.path.exists(CONFIG_FILE):
        return {"github_token": ""}
    with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_config(config: Dict):
    """保存配置"""
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)

def detect_market(code: str) -> str:
    """检测股票市场"""
    code = code.upper()
    if code.startswith('HK'):
        return 'hk'
    if code.startswith('US'):
        return 'us'
    if code.startswith('SH') or code.startswith('SZ'):
        return 'a'
    if code.isdigit():
        if code.startswith('6') or code.startswith('5') or code.startswith('9'):
            return 'a'
        if code.startswith('0') or code.startswith('2') or code.startswith('3'):
            return 'a'
        if len(code) == 5:
            return 'hk'
    return 'us'

def format_code(code: str) -> str:
    """格式化股票代码"""
    code = code.strip().upper()
    if code.startswith(('SH', 'SZ', 'HK', 'US')):
        return code
    if code.isdigit() and len(code) == 6:
        if code.startswith(('6', '5', '9')):
            return 'SH' + code
        if code.startswith(('0', '2', '3')):
            return 'SZ' + code
    if code.isdigit() and len(code) == 5:
        return 'HK' + code
    if code.isalpha():
        return 'US' + code
    return code

# ==================== API 接口 ====================

@app.get("/")
async def root():
    return {"message": "股票管理工具 API", "version": "1.0.0"}

@app.get("/api/stocks", response_model=ApiResponse)
async def get_stocks():
    """获取所有股票"""
    try:
        data = load_data()
        return ApiResponse(success=True, message="获取成功", data=data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/stocks/{code}", response_model=ApiResponse)
async def get_stock(code: str):
    """获取单只股票"""
    code = format_code(code)
    data = load_data()
    for stock in data:
        if stock['code'] == code:
            return ApiResponse(success=True, message="获取成功", data=stock)
    raise HTTPException(status_code=404, detail="股票不存在")

@app.post("/api/stocks", response_model=ApiResponse)
async def add_stock(stock_input: StockInput):
    """添加股票"""
    try:
        code = format_code(stock_input.code)
        data = load_data()
        
        for stock in data:
            if stock['code'] == code:
                raise HTTPException(status_code=400, detail="股票已存在")
        
        name = stock_input.name
        if not name:
            quote = get_realtime_quote(code)
            if quote:
                name = quote.get('name', code)
        
        new_stock = {
            "code": code,
            "name": name or code,
            "market": stock_input.market or detect_market(code),
            "watchPrice": stock_input.watchPrice or 0,
            "watchDate": stock_input.watchDate or datetime.now().strftime('%Y-%m-%d'),
            "recommender": stock_input.recommender or "",
            "buyers": [b.dict() for b in stock_input.buyers] if stock_input.buyers else []
        }
        
        data.append(new_stock)
        save_data(data)
        
        return ApiResponse(success=True, message="添加成功", data=new_stock)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/stocks/{code}", response_model=ApiResponse)
async def update_stock(code: str, stock_input: StockInput):
    """更新股票"""
    try:
        code = format_code(code)
        data = load_data()
        
        for i, stock in enumerate(data):
            if stock['code'] == code:
                if stock_input.name:
                    data[i]['name'] = stock_input.name
                if stock_input.market:
                    data[i]['market'] = stock_input.market
                if stock_input.watchPrice is not None:
                    data[i]['watchPrice'] = stock_input.watchPrice
                if stock_input.watchDate:
                    data[i]['watchDate'] = stock_input.watchDate
                if stock_input.recommender is not None:
                    data[i]['recommender'] = stock_input.recommender
                if stock_input.buyers is not None:
                    data[i]['buyers'] = [b.dict() for b in stock_input.buyers]
                
                save_data(data)
                return ApiResponse(success=True, message="更新成功", data=data[i])
        
        raise HTTPException(status_code=404, detail="股票不存在")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/stocks/{code}", response_model=ApiResponse)
async def delete_stock(code: str):
    """删除股票"""
    try:
        code = format_code(code)
        data = load_data()
        
        for i, stock in enumerate(data):
            if stock['code'] == code:
                deleted = data.pop(i)
                save_data(data)
                return ApiResponse(success=True, message="删除成功", data=deleted)
        
        raise HTTPException(status_code=404, detail="股票不存在")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/stocks/{code}/quote", response_model=ApiResponse)
async def get_stock_quote(code: str):
    """获取实时行情（腾讯 API）"""
    code = format_code(code)
    try:
        quote = get_realtime_quote(code)
        if quote:
            return ApiResponse(success=True, message="获取成功", data=quote)
        raise HTTPException(status_code=404, detail="获取行情失败")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/stocks/{code}/history", response_model=ApiResponse)
async def get_stock_history(code: str, date: str):
    """获取历史数据（统一接口，可替换数据源）"""
    code = format_code(code)
    
    # 处理日期格式（支持 ISO 格式、带时间等）
    try:
        # 如果是 ISO 格式（2026-01-01T00:00:00.000Z），提取日期部分
        if 'T' in date:
            date = date.split('T')[0]
        # 验证日期格式
        datetime.strptime(date, '%Y-%m-%d')
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"日期格式错误：{date}，应为 YYYY-MM-DD")
    
    try:
        print(f"获取历史数据：{code} {date}")
        history = get_historical_data(code, date)
        if history:
            print(f"获取成功：{history}")
            return ApiResponse(success=True, message="获取成功", data=history)
        print(f"获取失败：无数据")
        raise HTTPException(status_code=404, detail="获取历史数据失败")
    except HTTPException:
        raise
    except Exception as e:
        print(f"获取历史数据异常：{e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/github/push", response_model=ApiResponse)
async def github_push(message: str = "Update stock data"):
    """推送到 GitHub"""
    try:
        config = load_config()
        token = config.get('github_token', '')
        
        print(f"GitHub Push 请求收到，Token 配置：{'是' if token else '否'}")
        
        if not token:
            print("❌ 未配置 GitHub Token")
            raise HTTPException(status_code=400, detail="请先配置 GitHub Token")
        
        os.chdir(BASE_DIR)
        print(f"工作目录：{BASE_DIR}")
        
        # git add
        result = subprocess.run(['git', 'add', 'stock-data.json'], check=True, capture_output=True)
        print("✅ git add 成功")
        
        # git commit
        commit_msg = f"{message} - {datetime.now().strftime('%Y/%m/%d %H:%M:%S')}"
        result = subprocess.run(['git', 'commit', '-m', commit_msg], check=True, capture_output=True)
        print(f"✅ git commit 成功：{commit_msg}")
        
        # git push（使用 token）
        env = os.environ.copy()
        # 设置 git 使用 token 认证
        print("🚀 开始 git push...")
        result = subprocess.run(
            ['git', '-c', f'credential.helper=store', 'push', 'origin', 'main'],
            check=True,
            capture_output=True,
            env=env,
            timeout=60
        )
        print("✅ git push 成功")
        
        return ApiResponse(success=True, message="推送成功")
    except subprocess.TimeoutExpired:
        print("❌ git push 超时")
        raise HTTPException(status_code=500, detail="Git 推送超时，请检查网络连接")
    except subprocess.CalledProcessError as e:
        stderr = e.stderr.decode() if e.stderr else str(e)
        print(f"❌ Git 操作失败：{stderr}")
        raise HTTPException(status_code=500, detail=f"Git 操作失败：{stderr}")
    except Exception as e:
        print(f"❌ 推送异常：{e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/github/status", response_model=ApiResponse)
async def github_status():
    """获取 GitHub 状态"""
    try:
        config = load_config()
        os.chdir(BASE_DIR)
        result = subprocess.run(['git', 'status', '--porcelain'], capture_output=True, text=True)
        has_changes = bool(result.stdout.strip())
        result = subprocess.run(['git', 'log', '--oneline', '-5'], capture_output=True, text=True)
        recent_commits = result.stdout.strip().split('\n') if result.stdout else []
        
        return ApiResponse(success=True, message="获取成功", data={
            "has_changes": has_changes,
            "recent_commits": recent_commits,
            "token_configured": bool(config.get('github_token', ''))
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/config", response_model=ApiResponse)
async def update_config(github_token: str):
    """更新配置"""
    try:
        config = load_config()
        config['github_token'] = github_token
        save_config(config)
        return ApiResponse(success=True, message="配置已保存")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/config", response_model=ApiResponse)
async def get_config():
    """获取配置"""
    try:
        config = load_config()
        return ApiResponse(success=True, message="获取成功", data={
            "github_token_configured": bool(config.get('github_token', ''))
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==================== 启动服务 ====================

if __name__ == "__main__":
    import uvicorn
    print("🚀 股票管理工具后端服务启动中...")
    print(f"   数据文件：{DATA_FILE}")
    print(f"   实时行情：腾讯 API")
    print(f"   历史数据：AkShare (可替换)")
    print(f"   访问地址：http://localhost:8766")
    uvicorn.run(app, host="0.0.0.0", port=8766)
