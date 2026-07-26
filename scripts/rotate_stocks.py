#!/usr/bin/env python3
"""行业轮动选股 - 根据信号自动替换长期无机会的股票"""
import json, os, random, sys
from datetime import datetime, timedelta

POOL_FILE = "stock_pool.json"
STATE_FILE = "stock_state.json"
SIGNAL_LOG = f"logs/stock_analysis_{datetime.now().strftime('%Y%m%d')}.log"
MAX_NO_SIGNAL = 5  # 连续5次无信号就轮换

def load_pool():
    with open(POOL_FILE) as f:
        return json.load(f)

def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            return json.load(f)
    return {"no_signal_count": {}, "current_stocks": []}

def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)

def get_signals():
    """解析日志中哪些股票有买卖信号"""
    import re
    signals = set()
    if os.path.exists(SIGNAL_LOG):
        with open(SIGNAL_LOG) as f:
            for line in f:
                m = re.search(r'\|.*?(\w[\w\s.]+)\((\w+)\):\s*([\u4e00-\u9fff/]+)\s*\|\s*评分\s*(\d+)', line)
                if m:
                    code = m.group(2)
                    advice = m.group(3)
                    score = int(m.group(4))
                    if score >= 60 or score <= 40 or advice in ("买入","卖出","减仓","强烈看空","加仓"):
                        signals.add(code)
    return signals

def select_stocks(pool, state, signals):
    """根据信号和轮动规则选择股票"""
    pool_by_sector = {s["name"]: s["pools"] for s in pool["sectors"]}
    weights = {s["name"]: s["weight"] for s in pool["sectors"]}
    
    no_signal = state.get("no_signal_count", {})
    current = state.get("current_stocks", [])
    today = datetime.now().strftime("%Y%m%d")
    
    # 更新计数
    for code in current:
        if code in signals:
            no_signal[code] = 0  # 有信号重置
        else:
            no_signal[code] = no_signal.get(code, 0) + 1  # 无信号+1
    
    new_stocks = []
    all_sectors = [s for s in pool["sectors"]]
    random.shuffle(all_sectors)  # 随机顺序
    
    for sector in all_sectors:
        name = sector["name"]
        pools = list(sector["pools"])
        weight = sector["weight"]
        random.shuffle(pools)
        
        count = 0
        for code in pools:
            if count >= weight:
                break
            # 已经在别的组选过了
            if code in new_stocks:
                continue
            # 检查是否需要轮换
            if code in no_signal and no_signal[code] >= MAX_NO_SIGNAL and len([c for c in pools if c not in new_stocks]) > weight:
                continue  # 无信号太久，跳过
            new_stocks.append(code)
            count += 1
    
    # 如果不够15只，从剩余池子补
    all_pool = []
    for s in pool["sectors"]:
        for c in s["pools"]:
            if c not in new_stocks:
                all_pool.append(c)
    random.shuffle(all_pool)
    while len(new_stocks) < 15 and all_pool:
        c = all_pool.pop(0)
        if c not in new_stocks:
            new_stocks.append(c)
    
    # 更新状态
    state["no_signal_count"] = no_signal
    state["current_stocks"] = new_stocks
    state["last_updated"] = today
    save_state(state)
    
    return new_stocks[:15]

def main():
    pool = load_pool()
    state = load_state()
    signals = get_signals()
    
    stocks = select_stocks(pool, state, signals)
    result = ",".join(stocks)
    
    print(f"STOCK_LIST={result}")
    print(f"SELECTED: {len(stocks)} stocks")
    
    # 输出变动
    old = set(state.get("current_stocks", []))
    new = set(stocks)
    added = new - old
    removed = old - new
    if added:
        print(f"➕ 新增: {','.join(sorted(added))}")
    if removed:
        print(f"➖ 移除: {','.join(sorted(removed))}")
    
    # 更新 GitHub Actions 变量
    if os.environ.get("GITHUB_ENV"):
        with open(os.environ["GITHUB_ENV"], "a") as f:
            f.write(f"STOCK_LIST_CONFIG={result}\n")
            f.write(f"STOCK_LIST={result}\n")

if __name__ == "__main__":
    main()
