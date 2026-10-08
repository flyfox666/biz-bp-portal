"""各页面共用：缓存、排队抓取、状态展示。

降低反爬风险的三道保险（所有访问者共享）:
1. 缓存优先：相同条件 CACHE_TTL 内直接复用，打开页面也只展示上次结果，不自动抓取。
2. 排队：同一时刻只允许一个抓取在跑，其他人等待（等到后会命中刚抓好的缓存）。
3. 冷却：同一数据源两次真实抓取之间至少间隔 COOLDOWN 秒。
"""
from __future__ import annotations

import asyncio
import threading
import time
from datetime import datetime
from typing import Any

import streamlit as st

from scraper_kit.registry import discover_scrapers
from scraper_kit.runner import run_scraper

CACHE_TTL = 30 * 60
COOLDOWN = 60

SCRAPERS = {s.source_id: s for s in discover_scrapers()}
SHORT_NAME = {sid: s.name.split(" (")[0] for sid, s in SCRAPERS.items()}

# 链家城市代码 -> 中文名（前 4 个为项目默认；其余未逐一验证，抓不到会显示兜底数据）
LIANJIA_CITY_OPTIONS = {
    "bj": "北京", "sh": "上海", "sz": "深圳", "gz": "广州",
    "cd": "成都", "hz": "杭州", "nj": "南京", "wh": "武汉", "cq": "重庆",
    "tj": "天津", "su": "苏州", "xa": "西安", "cs": "长沙", "qd": "青岛",
    "zz": "郑州", "dg": "东莞", "fs": "佛山", "sy": "沈阳", "dl": "大连",
    "jn": "济南", "hf": "合肥", "xm": "厦门", "fz": "福州",
}
DEFAULT_CITIES = ["bj", "sh", "sz", "gz"]


class TooSoon(Exception):
    """距离上一次真实抓取太近。"""


@st.cache_resource
def _state() -> dict[str, Any]:
    return {"cache": {}, "lock": threading.Lock(), "last_live": {}}


def _key(source_id: str, cities: tuple[str, ...]) -> tuple:
    return (source_id, cities)


def peek(source_id: str, cities: tuple[str, ...] = ()) -> dict[str, Any] | None:
    """只读缓存，不触发抓取。"""
    return _state()["cache"].get(_key(source_id, cities))


def run_cached(source_id: str, cities: tuple[str, ...] = (), force: bool = False) -> tuple[dict, bool]:
    """返回 (结果, 是否来自缓存)。可能抛 TooSoon。"""
    st_ = _state()
    key = _key(source_id, cities)

    def fresh() -> dict | None:
        hit = st_["cache"].get(key)
        if hit and not force and time.time() - hit["at"] < CACHE_TTL:
            return hit
        return None

    if (hit := fresh()):
        return hit, True
    with st_["lock"]:  # 排队：同一时刻只有一个真实抓取
        if (hit := fresh()):  # 排队期间别人可能刚抓过
            return hit, True
        wait = COOLDOWN - (time.time() - st_["last_live"].get(source_id, 0))
        if wait > 0:
            raise TooSoon(f"该数据源 {int(wait)} 秒前刚抓取过，请 {int(wait)} 秒后再试（或直接使用已有结果）。")
        s = SCRAPERS[source_id]
        if source_id == "lianjia_deals":
            s.cities = [(c, LIANJIA_CITY_OPTIONS.get(c, c)) for c in cities]
        result = asyncio.run(run_scraper(s))
        result["at"] = time.time()
        st_["cache"][key] = result
        st_["last_live"][source_id] = time.time()
        return result, False


def fmt_time(ts: float) -> str:
    return datetime.fromtimestamp(ts).strftime("%m-%d %H:%M:%S")


def render_status(result: dict[str, Any] | None, cached: bool | None = None) -> None:
    if result is None:
        st.info("还没有数据。点击上方“开始抓取”获取。")
        return
    name = SHORT_NAME.get(result["s"].source_id, "")
    when = fmt_time(result["at"])
    if result["fallback"]:
        st.error(f"**{name}**：{len(result['rows'])} 行 —— ⚠️ 兜底数据，**不是真实数据**。"
                 f"原因：{result['error'][:150]}（{when}）")
    else:
        tail = "，使用缓存结果" if cached else ""
        st.success(f"**{name}**：{len(result['rows'])} 行 —— 实时数据（{when}{tail}）")


def do_fetch(source_id: str, cities: tuple[str, ...] = (), force: bool = False) -> None:
    try:
        with st.spinner("抓取中（若有人正在抓取需排队等待，链家有请求间隔，可能需要十几秒）…"):
            result, cached = run_cached(source_id, cities, force)
        st.session_state[f"cached_{source_id}"] = cached
    except TooSoon as exc:
        st.warning(str(exc))
