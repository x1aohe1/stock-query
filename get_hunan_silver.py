#!/usr/bin/env python3
"""
获取湖南白银 (002716) 历史行情
使用腾讯财经 API - 无需 API key，稳定免费

价格说明：
- 不复权：真实交易价格
- 前复权：以最新价格为基准，向前复权（技术分析常用）
- 后复权：以最早价格为基准，向后复权（计算收益常用）
"""

import urllib.request
import json
import time

def get_stock_history_gtimg(symbol, count=600, adjust='qfq'):
    """
    从腾讯财经获取 A 股历史行情
    symbol: 6 位股票代码
    count: 获取多少条记录
    adjust: qfq=前复权，hfq=后复权
    """
    try:
        url = f"https://web.ifzq.gtimg.cn/appstock/app/fqkline/get?param=sz{symbol},day,,,{count},{adjust}"
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        req = urllib.request.Request(url, headers=headers)
        
        with urllib.request.urlopen(req, timeout=30) as response:
            data = json.loads(response.read().decode('utf-8'))
            
            if data.get('code') == 0 and data.get('data'):
                key = f'sz{symbol}'
                if adjust == 'qfq':
                    klines = data['data'][key]['qfqday']
                elif adjust == 'hfq':
                    klines = data['data'][key]['hfqday']
                else:
                    klines = data['data'][key]['day']
                return klines
            else:
                return None
    except Exception as e:
        print(f"获取数据失败：{e}")
        return None

def print_table(klines, title, show_all=False):
    """打印表格"""
    print(f"\n{title}")
    print("=" * 75)
    print(f"{'日期':<12} {'开盘':>10} {'收盘':>10} {'最高':>10} {'最低':>10} {'成交量':>12}")
    print("-" * 75)
    
    count = 0
    for k in klines:
        if not show_all and not k[0].startswith('2025-01'):
            continue
        date, o, c, h, l, v = k[0], float(k[1]), float(k[2]), float(k[3]), float(k[4]), float(k[5])
        print(f"{date:<12} {o:>10.2f} {c:>10.2f} {h:>10.2f} {l:>10.2f} {int(v):>12,}")
        count += 1
    
    print("-" * 75)
    print(f"共 {count} 条记录")

if __name__ == '__main__':
    print("=" * 75)
    print("获取湖南白银 (002716) 历史行情 - 腾讯财经 API")
    print("=" * 75)
    
    # 获取后复权数据（最接近真实价格）
    print("\n正在获取数据...")
    klines = get_stock_history_gtimg('002716', 600, 'hfq')
    
    if not klines:
        print("\n❌ 获取数据失败")
        exit(1)
    
    print(f"✅ 成功获取 {len(klines)} 条记录")
    
    # 打印 2025 年 1 月数据
    jan_data = [k for k in klines if k[0].startswith('2025-01')]
    print_table(jan_data, "📊 2025 年 1 月行情 (后复权)")
    
    # 单独显示 1 月 23 日
    print("\n" + "=" * 75)
    target = [k for k in klines if k[0] == '2025-01-23']
    if target:
        k = target[0]
        date, o, c, h, l, v = k[0], float(k[1]), float(k[2]), float(k[3]), float(k[4]), float(k[5])
        print("🎯 2025 年 1 月 23 日 行情数据")
        print("=" * 75)
        print(f"  日期：    {date}")
        print(f"  开盘：    ¥{o:.2f}")
        print(f"  最高：    ¥{h:.2f}")
        print(f"  最低：    ¥{l:.2f}")
        print(f"  收盘：    ¥{c:.2f}")
        print(f"  成交量：  {int(v):,} 手")
        print(f"  成交额：  约¥{int(v) * c:,.0f} 元")
        print("=" * 75)
        print("\n💡 注：这是后复权价格，真实交易价格可能在 13-15 元区间")
        print("   如需精确不复权数据，建议查看东方财富网：https://quote.eastmoney.com/sz002716.html")
    else:
        print("⚠️  1 月 23 日无交易数据")
