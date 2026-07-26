#!/usr/bin/env python3
"""筛选买卖信号并推送（带价格详情）"""
import json, os, re, urllib.request
from datetime import datetime

today = datetime.now().strftime("%Y%m%d")
report_file = f"reports/report_{today}.md"

if not os.path.exists(report_file):
    print(f"📭 报告不存在")
    exit(0)

with open(report_file, encoding='utf-8', errors='replace') as f:
    content = f.read()

# Step 1: 从摘要区解析评分和信号
summary_signals = {}  # code -> {score, signal_type, advice}
for line in content.split('\n'):
    # 匹配: **Apple Inc.(AAPL)**: 持有 | 评分 59 | 看多
    m = re.search(r'\*\*(.+?)\((\w+)\)\*\*:\s*(\S+)\s*\|\s*评分\s*(\d+)', line)
    if m:
        code = m.group(2)
        score = int(m.group(4))
        advice = m.group(3)
        
        signal_type = None
        if score >= 60:
            signal_type = "🟢 买入"
        elif score <= 40:
            signal_type = "🔴 做空/卖出"
        else:
            continue
        
        summary_signals[code] = {
            "name": m.group(1).strip(),
            "score": score,
            "signal": signal_type,
            "advice": advice
        }

if not summary_signals:
    print(f"📭 今日无买卖信号（{today}）")
    exit(0)

# Step 2: 从个股详情区提取价格/风险
stock_blocks = {}
current_code = None
for line in content.split('\n'):
    cm = re.search(r'^##\s+(?:🟢|🟡|🟠|🔴)?\s*(.+?)\s*\((\w+)\)', line)
    if cm:
        current_code = cm.group(2)
        stock_blocks[current_code] = []
    elif current_code:
        stock_blocks[current_code].append(line)

# Step 3: 构造每条信号
signals = []
for code, info in summary_signals.items():
    block = "\n".join(stock_blocks.get(code, []))
    
    msg = f"{info['signal']} *{info['name']}* ({code}) — *{info['score']}分* | {info['advice']}"
    
    # 价格
    price_m = re.search(r'\|\s*当前价\s*\|\s*([\d.]+)', block)
    close_m = re.search(r'\|\s*([\d.]+)\s*\|\s*[\d.]+\s*\|\s*[\d.]+', block)
    support_m = re.search(r'\|\s*支撑位\s*\|\s*([\d.]+)', block)
    resist_m = re.search(r'\|\s*压力位\s*\|\s*([\d.]+)', block)
    ma5_m = re.search(r'\|\s*MA5\s*\|\s*([\d.]+)', block)
    
    price_str = ""
    if close_m:
        price_str += f"💰 ${close_m.group(1)}"
    if price_m:
        price_str += f" | 当前 ${price_m.group(1)}"
    if price_str:
        msg += "\n   " + price_str
    
    levels = []
    if ma5_m:
        levels.append(f"MA5 ${ma5_m.group(1)}")
    if support_m:
        levels.append(f"📉 ${support_m.group(1)}")
    if resist_m:
        levels.append(f"📈 ${resist_m.group(1)}")
    if levels:
        msg += "\n   " + " | ".join(levels)
    
    # 风险
    risk_match = re.search(r'\*\*🚨\s*风险警报\*\*.*?\n([\s\S]*?)(?=\*\*✨|\*\*📢|\*\*###|\Z)', block, re.DOTALL)
    if risk_match:
        risks = re.findall(r'-\s*(.+?)(?:\n|$)', risk_match.group(1))
        for r in risks[:2]:
            msg += f"\n   ⚠️ {r[:60]}"
    
    # 催化
    cat_match = re.search(r'\*\*✨\s*利好催化\*\*.*?\n([\s\S]*?)(?=\*\*🚨|\*\*📢|\*\*###|\Z)', block, re.DOTALL)
    if cat_match:
        cats = re.findall(r'-\s*(.+?)(?:\n|$)', cat_match.group(1))
        for c in cats[:1]:
            msg += f"\n   ✨ {c[:60]}"
    
    signals.append(msg)

# Step 4: 推送
TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")
if not TOKEN or not CHAT_ID:
    print("⚠️ 未配置 Telegram")
    exit(0)

header = f"📊 *信号提醒* {today}\n共 {len(signals)} 条\n\n"
for i in range(0, len(signals), 3):
    chunk = signals[i:i+3]
    msg = header + "\n".join(chunk)
    data = json.dumps({"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"}).encode()
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{TOKEN}/sendMessage",
        data=data, headers={"Content-Type": "application/json"})
    try:
        resp = json.loads(urllib.request.urlopen(req).read())
        print(f"✅ 信号组 {i//3+1} 已发送" if resp.get("ok") else f"⚠️ 发送失败: {resp.get('description','')}")
    except Exception as e:
        print(f"❌ 发送异常: {e}")
    header = ""
