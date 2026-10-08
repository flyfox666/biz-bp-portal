"""独立爬虫小工具 demo：依次运行三个爬虫，输出 Excel + 终端摘要。

用法:
    .venv/bin/python run_demo.py                 # 三个都跑
    .venv/bin/python run_demo.py nbs_house_price # 只跑一个
"""
from __future__ import annotations

import asyncio
import sys
import time
from datetime import datetime
from pathlib import Path

from openpyxl import Workbook

from scraper_kit.registry import discover_scrapers, get_all

OUT = Path(__file__).parent / "output"


async def run_scraper(s):
    """复刻 BaseScraper.run，但保留数据行，并明确标出是否为兜底数据。"""
    t0 = time.perf_counter()
    try:
        rows = s.validate(s.parse(await s.fetch()))
        status, err, fb = "实时数据", "", False
    except Exception as exc:  # noqa: BLE001
        rows = s.validate(s.fallback())
        status, err, fb = "兜底(非真实)数据", f"{type(exc).__name__}: {exc}", True
    return {"s": s, "rows": rows, "status": status, "error": err, "fallback": fb,
            "ms": int((time.perf_counter() - t0) * 1000)}


async def main(only: list[str]):
    scrapers = [s for s in discover_scrapers() if not only or s.source_id in only]
    results = [await run_scraper(s) for s in scrapers]
    OUT.mkdir(exist_ok=True)
    wb = Workbook()
    wb.remove(wb.active)
    summary = wb.create_sheet("运行摘要")
    summary.append(["来源", "状态", "行数", "耗时ms", "失败原因"])
    for r in results:
        s = r["s"]
        summary.append([s.name, r["status"], len(r["rows"]), r["ms"], r["error"]])
        ws = wb.create_sheet(s.source_id[:31])
        if r["rows"]:
            cols = list(r["rows"][0].keys())
            ws.append(cols)
            for row in r["rows"]:
                ws.append([row.get(c) for c in cols])
        print(f"[{r['status']}] {s.name}: {len(r['rows'])} 行, {r['ms']}ms" + (f"\n    原因: {r['error'][:200]}" if r["error"] else ""))
    path = OUT / f"scrape_{datetime.now():%Y%m%d_%H%M%S}.xlsx"
    wb.save(path)
    print("已输出:", path)


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1:]))
