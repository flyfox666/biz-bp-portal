"""链家二手房页：抓取条件(决定请求) + 结果筛选(本地，不发请求) + 汇总。"""
import io
from datetime import datetime

import pandas as pd
import streamlit as st

from scraper_kit.runner import build_workbook, to_records
from ui import common as C

SID = "lianjia_deals"
st.title("链家二手房（挂牌）")
st.caption("每个城市只取列表第 1 页（约 30 套），是样本不是全量。价格为挂牌价，不是成交价。")

# ---- 抓取条件 ----
with st.container(border=True):
    st.subheader("抓取条件")
    cities = st.multiselect("城市", list(C.LIANJIA_CITY_OPTIONS), default=C.DEFAULT_CITIES,
                            format_func=lambda c: f"{C.LIANJIA_CITY_OPTIONS[c]} ({c})")
    extra = st.text_input("补充城市（代码:名称，逗号分隔）", placeholder="例如 wx:无锡, nb:宁波")
    for part in filter(None, (p.strip() for p in extra.replace("，", ",").replace("：", ":").split(","))):
        if ":" in part:
            code, name = (x.strip() for x in part.split(":", 1))
            if code.isalpha() and code.islower():
                C.LIANJIA_CITY_OPTIONS[code] = name
                if code not in cities:
                    cities.append(code)
    c1, c2 = st.columns([1, 3])
    force = c2.checkbox("忽略缓存，强制重新抓取", value=False)
    if c1.button("开始抓取", type="primary", disabled=not cities):
        C.do_fetch(SID, tuple(cities), force)

result = C.peek(SID, tuple(cities))
C.render_status(result, st.session_state.get(f"cached_{SID}"))
if result is None or not result["rows"]:
    st.stop()

cols, rows = to_records(result)
df = pd.DataFrame(rows, columns=cols)
if result["fallback"]:
    st.warning("以下为兜底数据，仅用于演示格式，不含户型、面积等明细字段。")

# ---- 结果筛选（本地，不发请求）----
UP, TP, AR = "挂牌单价(元/平方米)", "挂牌总价(万元)", "面积(平方米)"
with st.container(border=True):
    st.subheader("结果筛选（不会产生新请求）")
    a, b, c = st.columns(3)
    sel_city = a.multiselect("城市 ", sorted(df["城市"].dropna().unique()))
    sel_dist = b.multiselect("区域", sorted(df["区域"].dropna().unique()))
    kw = c.text_input("关键词（小区/标题/标签）")
    d, e, f = st.columns(3)
    sel_layout = d.multiselect("户型", sorted(df["户型"].dropna().unique()))
    sel_ori = e.multiselect("朝向", sorted(df["朝向"].dropna().unique()))
    sel_dec = f.multiselect("装修", sorted(df["装修"].dropna().unique()))
    g, h, i = st.columns(3)
    sel_type = g.multiselect("楼型", sorted(df["楼型"].dropna().unique()))
    sel_floor = h.multiselect("楼层", ["低楼层", "中楼层", "高楼层"])
    min_year = i.number_input("建成年份不早于（0=不限）", 0, 2100, 0, step=1)

    def rng(label, col, container):
        s = df[col].dropna()
        if s.empty or s.min() == s.max():
            return None
        return container.slider(label, float(s.min()), float(s.max()), (float(s.min()), float(s.max())))

    p1, p2 = st.columns(2)
    tp_rng = rng("总价区间(万元)", TP, p1)
    ar_rng = rng("面积区间(平方米)", AR, p2)

m = pd.Series(True, index=df.index)
if sel_city: m &= df["城市"].isin(sel_city)
if sel_dist: m &= df["区域"].isin(sel_dist)
if sel_layout: m &= df["户型"].isin(sel_layout)
if sel_ori: m &= df["朝向"].isin(sel_ori)
if sel_dec: m &= df["装修"].isin(sel_dec)
if sel_type: m &= df["楼型"].isin(sel_type)
if sel_floor: m &= df["楼层"].fillna("").apply(lambda x: any(x.startswith(k) for k in sel_floor))
if min_year: m &= df["建成年份"].fillna(0) >= min_year
if tp_rng: m &= df[TP].between(*tp_rng) | df[TP].isna()
if ar_rng: m &= df[AR].between(*ar_rng) | df[AR].isna()
if kw:
    hay = df[["小区", "房源标题", "房源标签"]].fillna("").agg(" ".join, axis=1)
    m &= hay.str.contains(kw, case=False, regex=False)
fdf = df[m]

# ---- 汇总 ----
k1, k2, k3, k4 = st.columns(4)
k1.metric("房源数(套)", len(fdf))
k2.metric("平均挂牌单价(元/平方米)", f"{fdf[UP].mean():,.0f}" if fdf[UP].notna().any() else "-")
k3.metric("中位数挂牌单价(元/平方米)", f"{fdf[UP].median():,.0f}" if fdf[UP].notna().any() else "-")
k4.metric("中位数挂牌总价(万元)", f"{fdf[TP].median():,.0f}" if fdf[TP].notna().any() else "-")
st.caption("挂牌价里的极端高价房源会拉高平均数，财务对比建议以中位数为主。")

if not result["fallback"] and not fdf.empty:
    g = fdf.groupby(["城市", "区域"])[UP].agg(["median", "mean", "count"]).round(0).reset_index()
    g.columns = ["城市", "区域", "中位数单价(元/平方米)", "平均单价(元/平方米)", "房源数(套)"]
    g = g.sort_values("中位数单价(元/平方米)", ascending=False)
    st.markdown("**区域挂牌单价对比**")
    st.bar_chart(g.assign(区域标签=g["城市"] + "-" + g["区域"]).set_index("区域标签")["中位数单价(元/平方米)"])
    st.dataframe(g, hide_index=True, width="stretch")

st.markdown(f"**明细（{len(fdf)} 条）**")
st.dataframe(fdf, hide_index=True, width="stretch")
buf = io.BytesIO()
build_workbook([result]).save(buf)
st.download_button("下载本页数据 (Excel，含全部未筛选数据)", buf.getvalue(),
                   file_name=f"链家二手房_{datetime.now():%Y%m%d_%H%M}.xlsx",
                   mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
