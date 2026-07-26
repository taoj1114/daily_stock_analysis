#!/usr/bin/env python3
"""快速分析指定股票"""
import os, sys

codes = [c.strip().upper() for c in sys.argv[1].split(",")]

os.environ["SCHEDULE_ENABLED"] = "false"
os.environ["RUN_IMMEDIATELY"] = "false"

from src.core.pipeline import StockAnalysisPipeline
from src.config import get_config

config = get_config()
pipeline = StockAnalysisPipeline(config)
results = pipeline.run(stock_codes=codes)

for r in results if results else []:
    code = r.get("code", "?")
    analysis = r.get("analysis") or {}
    if not analysis:
        print(f"[{code}] 无分析结果")
        continue
    score = analysis.get("sentiment_score", "?")
    phase = analysis.get("phase_decision", {}) or {}
    signal = phase.get("signal", "?")
    conclusion = (analysis.get("dashboard", {}) or {}).get("core_conclusion", {}) or {}
    sentence = conclusion.get("one_sentence", "")
    print(f"[{code}] 评分: {score} | 信号: {signal}")
    if sentence:
        print(f"  → {sentence}")
