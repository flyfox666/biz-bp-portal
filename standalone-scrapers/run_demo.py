"""命令行版：依次运行爬虫，输出 Excel + 终端摘要。

用法:
    python run_demo.py                 # 三个都跑
    python run_demo.py nbs_house_price # 只跑一个
网页版见 app.py (streamlit run app.py)。
"""
from __future__ import annotations

import asyncio
import sys
from datetime import datetime
from pathlib import Path

from scraper_kit.registry import discover_scrapers
from scraper_kit.runner import build_workbook, run_scraper

OUT = Path(__file__).parent / "output"


async def main(only: list[str]):
    scrapers = [s for s in discover_scrapers() if not only or s.source_id in only]
    results = [await run_scraper(s) for s in scrapers]
    for r in results:
        print(f"[{r['status']}] {r['s'].name}: {len(r['rows'])} 行, {r['ms']}ms"
              + (f"\n    原因: {r['error'][:200]}" if r["error"] else ""))
    OUT.mkdir(exist_ok=True)
    path = OUT / f"scrape_{datetime.now():%Y%m%d_%H%M%S}.xlsx"
    build_workbook(results).save(path)
    print("已输出:", path)


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1:]))
