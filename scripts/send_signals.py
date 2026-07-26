#!/usr/bin/env python3
"""筛选买卖信号并推送 Telegram"""
import json, os, re, sys
from datetime import datetime

today = datetime.now().strftime("%Y%m%d")
log_file = f"logs/stock_analysis_{today}.log"

signals = []

if os.path.exists(log_file):
    with open(log_file) as f:
        for line in f:
            m = re.search(r'(\w[\w.]+)\((\w+)\):\s*(\S+)\s*\|\s*评分\s*(\d+)', line)
            if m:
                name, code, advice, score = m.group(1), m.group(2), m.group(3), int(m.group(4))
                signal = None
                if score >= 60 and advice in ("买入","持有","持有观察","加仓"):
                    signal = "🟢 买入"
                elif score <= 40 or advice in ("卖出","减仓","强烈看空"):
                    signal = "🔴 做空/卖出"
                if signal:
                    signals.append(f"{signal} {name}({code}) — 评分 {score} | {advice}")

if signals:
    TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")
    if TOKEN and CHAT_ID:
        msg = f"📊 信号提醒 {today}\n\n" + "\n".join(signals)
        import urllib.request
        data = json.dumps({"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"}).encode()
        req = urllib.request.Request(
            f"https://api.telegram.org/bot{TOKEN}/sendMessage",
            data=data, headers={"Content-Type": "application/json"})
        resp = json.loads(urllib.request.urlopen(req).read())
        print("✅ 信号通知已发送" if resp.get("ok") else f"⚠️ 发送失败: {resp.get('description','')}")
    else:
        print("⚠️ 未配置 Telegram")
else:
    print("📭 今日无明确买卖信号")
