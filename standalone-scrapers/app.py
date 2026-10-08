"""网页版：streamlit run app.py

选择爬虫（链家可选城市）→ 开始抓取 → 查看状态/数据 → 下载 Excel。
"""
from __future__ import annotations

import asyncio
import io
import time
from datetime import datetime

import pandas as pd
import streamlit as st

from scraper_kit.registry import discover_scrapers
from scraper_kit.runner import build_workbook, run_scraper, to_records

st.set_page_config(page_title="房地产数据抓取工具", layout="wide")

# 链家城市代码 -> 中文名。前 4 个是原项目默认；其余是常见城市的子域名代码，
# 未逐一验证页面格式一致，抓不到时状态会显示为"兜底数据"。可在下方输入框补充。
LIANJIA_CITY_OPTIONS = {
    "bj": "北京", "sh": "上海", "sz": "深圳", "gz": "广州",
    "cd": "成都", "hz": "杭州", "nj": "南京", "wh": "武汉", "cq": "重庆",
    "tj": "天津", "su": "苏州", "xa": "西安", "cs": "长沙", "qd": "青岛",
    "zz": "郑州", "dg": "东莞", "fs": "佛山", "sy": "沈阳", "dl": "大连",
    "jn": "济南", "hf": "合肥", "xm": "厦门", "fz": "福州",
}
DEFAULT_CITIES = ["bj", "sh", "sz", "gz"]
CACHE_TTL = 30 * 60  # 同样条件 30 分钟内复用上次结果，避免多人重复请求被反爬

SCRAPERS = {s.source_id: s for s in discover_scrapers()}


@st.cache_resource
def _cache() -> dict:
    """进程内缓存，所有访问者共享。key=(source_id, cities)。"""
    return {}


def run_cached(source_id: str, cities: tuple[str, ...], force: bool):
    key = (source_id, cities)
    cache = _cache()
    hit = cache.get(key)
    if hit and not force and time.time() - hit["at"] < CACHE_TTL:
        return hit, True
    s = SCRAPERS[source_id]
    if source_id == "lianjia_deals":
        s.cities = [(c, LIANJIA_CITY_OPTIONS.get(c, c)) for c in cities]
    result = asyncio.run(run_scraper(s))
    result["at"] = time.time()
    cache[key] = result
    return result, False


st.title("房地产数据抓取工具")
st.caption("数据来源：国家统计局、链家（挂牌）、住建部。链家价格为**挂牌价，不是成交价**。")

with st.sidebar:
    st.header("选择数据源")
    chosen = [sid for sid, s in SCRAPERS.items() if st.checkbox(s.name.split(" (")[0], value=True, key=sid)]
    cities: list[str] = list(DEFAULT_CITIES)
    if "lianjia_deals" in chosen:
        st.subheader("链家城市")
        cities = st.multiselect(
            "城市", options=list(LIANJIA_CITY_OPTIONS), default=DEFAULT_CITIES,
            format_func=lambda c: f"{LIANJIA_CITY_OPTIONS[c]} ({c})",
        )
        extra = st.text_input("补充城市(代码:名称，逗号分隔)", placeholder="例如 wx:无锡, nb:宁波")
        for part in filter(None, (p.strip() for p in extra.replace("，", ",").replace("：", ":").split(","))):
            if ":" in part:
                code, name = (x.strip() for x in part.split(":", 1))
                if code.isalpha() and code.islower():
                    LIANJIA_CITY_OPTIONS[code] = name
                    cities.append(code)
    force = st.checkbox("忽略缓存，强制重新抓取", value=False)
    go = st.button("开始抓取", type="primary", width="stretch", disabled=not chosen)

if go:
    results = []
    with st.spinner("抓取中，链家会有请求间隔，可能需要十几秒…"):
        for sid in chosen:
            if sid == "lianjia_deals" and not cities:
                st.warning("链家未选择城市，已跳过。")
                continue
            res, cached = run_cached(sid, tuple(cities) if sid == "lianjia_deals" else (), force)
            res["cached"] = cached
            results.append(res)
    st.session_state["results"] = results

results = st.session_state.get("results")
if not results:
    st.info("在左侧选择数据源后点击“开始抓取”。")
    st.stop()

st.subheader("运行状态")
for r in results:
    when = datetime.fromtimestamp(r["at"]).strftime("%H:%M:%S")
    note = f"（使用 {when} 的缓存结果）" if r["cached"] else f"（{when}）"
    if r["fallback"]:
        st.error(f"**{r['s'].name.split(' (')[0]}**：{len(r['rows'])} 行 —— ⚠️ 兜底数据，**不是真实数据**。原因：{r['error'][:150]} {note}")
    else:
        st.success(f"**{r['s'].name.split(' (')[0]}**：{len(r['rows'])} 行 —— 实时数据 {note}")

buf = io.BytesIO()
build_workbook(results).save(buf)
st.download_button("下载 Excel", buf.getvalue(), file_name=f"房地产数据_{datetime.now():%Y%m%d_%H%M}.xlsx",
                   mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

tabs = st.tabs([COLUMN_TITLE for COLUMN_TITLE in (r["s"].name.split(" (")[0] for r in results)])
for tab, r in zip(tabs, results):
    with tab:
        cols, rows = to_records(r)
        df = pd.DataFrame(rows, columns=cols)
        if r["fallback"]:
            st.warning("以下为兜底数据，仅用于演示格式。")
        if r["s"].source_id == "lianjia_deals" and not df.empty:
            c1, c2 = st.columns(2)
            sel_city = c1.multiselect("筛选城市", sorted(df["城市"].dropna().unique()))
            sel_dist = c2.multiselect("筛选区域", sorted(df["区域"].dropna().unique()))
            if sel_city:
                df = df[df["城市"].isin(sel_city)]
            if sel_dist:
                df = df[df["区域"].isin(sel_dist)]
            if not r["fallback"] and not df.empty:
                st.markdown("**区域平均挂牌单价(元/平方米)**（由单套房源现算）")
                avg = df.groupby(["城市", "区域"])["挂牌单价(元/平方米)"].agg(["mean", "count"]).round(0)
                avg.columns = ["平均挂牌单价(元/平方米)", "房源数(套)"]
                st.dataframe(avg.reset_index(), width="stretch", hide_index=True)
        st.dataframe(df, width="stretch", hide_index=True)
