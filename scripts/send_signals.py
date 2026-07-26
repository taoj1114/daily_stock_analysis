#!/usr/bin/env python3
"""筛选买卖信号并推送 Telegram（包含价格/风险详情）"""
import json, os, re, urllib.request
from datetime import datetime

today = datetime.now().strftime("%Y%m%d")
report_file = f"reports/report_{today}.md"

if not os.path.exists(report_file):
    print(f"📭 报告不存在: {report_file}")
    exit(0)

with open(report_file, encoding='utf-8', errors='replace') as f:
    content = f.read()

# 按股票拆分报告块
stock_blocks = re.split(r'\n## ', content)
signals = []

for block in stock_blocks:
    # 提取股票代码
    code_m = re.search(r'\((\w+)\)', block.split('\n')[0] if block else '')
    if not code_m:
        continue
    code = code_m.group(1)
    
    # 提取评分和结论
    score_m = re.search(r'评分\s*(\d+)', block)
    advice_m = re.search(r'\*\*(🟢|🟡|🟠|🔴)\*\*\s*([^\n]+)', block)
    
    if not score_m:
        continue
    score = int(score_m.group(1))
    
    signal_type = None
    advice = advice_m.group(2).strip() if advice_m else ""
    
    if score >= 60:
        signal_type = "🟢 买入"
    elif score <= 40:
        signal_type = "🔴 做空/卖出"
    else:
        continue  # 中性信号不推送
    
    # 提取名称
    name_m = re.search(r'\*\*(.+?)\s*\(' + code + r'\)', block)
    name = name_m.group(1).strip() if name_m else code
    
    # 提取价格（Markdown 表格格式）
    close_m = re.search(r'\|\s*([\d.]+)\s*\|\s*[\d.]+\s*\|\s*[\d.]+\s*\|\s*[\d.]+', block)
    price_m = re.search(r'\|\s*当前价\s*\|\s*([\d.]+)', block)
    support_m = re.search(r'\|\s*支撑位\s*\|\s*([\d.]+)', block)
    resist_m = re.search(r'\|\s*压力位\s*\|\s*([\d.]+)', block)
    ma5_m = re.search(r'\|\s*MA5\s*\|\s*([\d.]+)', block)
    
    # 提取买卖建议中的价格
    buy_m = re.search(r'买入.*?([\d.]+)', block)
    stop_m = re.search(r'止损.*?([\d.]+)', block)
    
    # 提取风险
    risks = re.findall(r'\*\*🚨\s*风险警报\*\*.*?\n([\s\S]*?)(?=\*\*✨|\*\*📢|\*\*###|\Z)', block)
    risk_text = ""
    if risks:
        risk_items = re.findall(r'-\s*(.+?)(?:\n|$)', risks[0])
        if risk_items:
            risk_text = "\n    ⚠️ " + "\n    ⚠️ ".join(r[:60] for r in risk_items[:2])
    
    # 提取催化
    cats = re.findall(r'\*\*✨\s*利好催化\*\*.*?\n([\s\S]*?)(?=\*\*🚨|\*\*📢|\*\*###|\Z)', block)
    cat_text = ""
    if cats:
        cat_items = re.findall(r'-\s*(.+?)(?:\n|$)', cats[0])
        if cat_items:
            cat_text = "\n    ✨ " + "\n    ✨ ".join(c[:60] for c in cat_items[:2])
    
    # 构建消息
    msg = f"{signal_type} *{name}* ({code}) — *{score}分*"
    # 价格线
    prices = []
    if close_m:
        prices.append(f"💰 ${close_m.group(1)}")
    if price_m:
        prices.append(f"当前 {price_m.group(1)}")
    if prices:
        msg += "\n   " + " | ".join(prices)
    if ma5_m:
        msg += f"\n   📊 MA5 ${ma5_m.group(1)}"
    if support_m:
        msg += f"\n   📉 支撑 ${support_m.group(1)}"
    if resist_m:
        msg += f"\n   📈 压力 ${resist_m.group(1)}"
    if risk_text:
        msg += risk_text
    if cat_text:
        msg += cat_text
    
    signals.append(msg)

if signals:
    TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")
    if TOKEN and CHAT_ID:
        header = f"📊 *信号提醒* {today}\n共 {len(signals)} 条\n\n"
        for i in range(0, len(signals), 3):
            chunk = signals[i:i+3]
            msg = header + "\n".join(chunk)
            data = json.dumps({"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"}).encode()
            req = urllib.request.Request(
                f"https://api.telegram.org/bot{TOKEN}/sendMessage",
                data=data, headers={"Content-Type": "application/json"})
            resp = json.loads(urllib.request.urlopen(req).read())
            if resp.get("ok"):
                print(f"✅ 信号组 {i//3 + 1} 已发送")
            else:
                print(f"⚠️ 发送失败: {resp.get('description','')}")
            header = ""  # 只有第一组带标题
    else:
        print("⚠️ 未配置 Telegram")
else:
    print(f"📭 今日无买卖信号（{today}）")
