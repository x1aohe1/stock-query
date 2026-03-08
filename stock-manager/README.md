# 股票管理工具

本地股票管理工具，支持 A 股、港股、美股的关注列表管理和收益计算。

---

## 🏗️ 架构说明

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   前端网页    │ ──▶ │   后端 API    │ ──▶ │   数据源     │
│  (Vue 3)      │     │  (FastAPI)   │     │ (腾讯/AkShare)│
│ :8767         │     │ :8766         │     │              │
└──────────────┘     └──────────────┘     └──────────────┘
```

### 数据流

1. **实时行情**：前端 → 后端 API → 腾讯 API → 返回 JSON
2. **历史数据**：前端 → 后端 API → AkShare → 返回 JSON
3. **数据存储**：stock-data.json（本地文件）+ GitHub（备份/共享）

---

## 📁 项目结构

```
stock-manager/
├── backend/
│   ├── main.py              # FastAPI 后端主程序
│   ├── data_sources.py      # 数据源模块（关键！）
│   └── requirements.txt     # Python 依赖
├── frontend/
│   └── index.html           # Vue 3 前端页面
├── stock-data.json          # 股票数据文件
├── config.json              # 配置文件（GitHub Token）
├── start.sh                 # Linux/Mac启动脚本
├── start.bat                # Windows 启动脚本
└── README.md                # 本文档
```

---

## 🚀 快速开始

### 1. 启动服务

```bash
cd stock-manager
./start.sh
```

### 2. 访问网页

- **管理版**：http://localhost:8767
- **API 文档**：http://localhost:8766/docs

### 3. 配置 GitHub Token（可选）

1. 访问 https://github.com/settings/tokens
2. 创建 Token（勾选 `repo` 权限）
3. 在网页中点击"设置"→输入 Token→保存

---

## 🔧 替换历史数据 API

当有新的历史数据 API 时，按以下步骤替换：

### 步骤 1：创建新的数据源类

编辑 `backend/data_sources.py`，添加新类：

```python
class NewAPIDataSource(HistoryDataSource):
    """新的历史数据 API"""
    
    def __init__(self, api_key: str = ''):
        self.api_key = api_key
    
    def get_history(self, code: str, date: str) -> Optional[Dict]:
        """
        实现历史数据获取逻辑
        
        返回格式：
        {
            'date': '2026-01-23',
            'open': 16.0,
            'close': 16.44,
            'high': 16.45,
            'low': 15.55,
            'note': '可选说明'
        }
        """
        # TODO: 调用新的 API
        # 示例：
        # response = requests.get(f'https://api.example.com/history?code={code}&date={date}')
        # data = response.json()
        # return {
        #     'date': date,
        #     'open': data['open'],
        #     ...
        # }
        pass

# 替换全局实例
history_source = NewAPIDataSource(api_key='your-api-key')
```

### 步骤 2：重启后端服务

```bash
pkill -f "python.*main.py"
./start.sh
```

### 步骤 3：测试

```bash
curl "http://localhost:8766/api/stocks/SZ002716/history?date=2026-01-23"
```

---

## 📊 API 接口

### 实时行情

```http
GET /api/stocks/{code}/quote
```

**示例**：
```bash
curl "http://localhost:8766/api/stocks/SZ002716/quote"
```

**响应**：
```json
{
    "success": true,
    "data": {
        "code": "SZ002716",
        "name": "湖南白银",
        "current": 14.87,
        "changePercent": 0.47
    }
}
```

### 历史数据

```http
GET /api/stocks/{code}/history?date={date}
```

**示例**：
```bash
curl "http://localhost:8766/api/stocks/SZ002716/history?date=2026-01-23"
```

**响应**：
```json
{
    "success": true,
    "data": {
        "date": "2026-01-23",
        "open": 16.0,
        "note": "使用 2026-01-23 的开盘价"
    }
}
```

### GitHub 推送

```http
POST /api/github/push
```

---

## ⚠️ 注意事项

1. **数据源模块**：`data_sources.py` 是核心，所有数据获取逻辑都在这里
2. **接口格式**：替换数据源时，保持 `get_history()` 的返回格式一致
3. **错误处理**：新 API 需要处理网络错误、数据解析错误等
4. **重试机制**：建议保留重试逻辑，提高稳定性

---

## 📝 待办事项

- [ ] 前端 Element Plus CDN 问题修复
- [ ] 批量操作功能
- [ ] 数据导出/导入
- [ ] 收益趋势图表
- [ ] 移动端适配

---

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

---

## 📄 许可证

MIT License
