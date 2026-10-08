"""住建部政策页。"""
import pandas as pd
import streamlit as st

from scraper_kit.runner import to_records
from ui import common as C

SID = "policy_crawler"
st.title("房地产政策")
if st.button("开始抓取", type="primary"):
    C.do_fetch(SID)
result = C.peek(SID)
C.render_status(result, st.session_state.get(f"cached_{SID}"))
if result is None or not result["rows"]:
    st.stop()

cols, rows = to_records(result)
df = pd.DataFrame(rows, columns=cols)
df["发布日期"] = pd.to_datetime(df["发布日期"], errors="coerce")
if result["fallback"]:
    st.warning("以下为预置的历史政策语料，不是实时抓取结果，仅用于演示格式。")

with st.container(border=True):
    a, b, c = st.columns(3)
    kw = a.text_input("关键词（标题/内容）")
    level = b.multiselect("级别", sorted(df["级别"].dropna().unique()))
    city = c.multiselect("城市", sorted(df["城市"].dropna().unique()))
    dmin, dmax = df["发布日期"].min(), df["发布日期"].max()
    rng = None
    if pd.notna(dmin) and dmin != dmax:
        rng = st.date_input("发布日期范围", (dmin.date(), dmax.date()), min_value=dmin.date(), max_value=dmax.date())

m = pd.Series(True, index=df.index)
if kw: m &= df[["标题", "内容摘要"]].fillna("").agg(" ".join, axis=1).str.contains(kw, case=False, regex=False)
if level: m &= df["级别"].isin(level)
if city: m &= df["城市"].isin(city)
if rng and len(rng) == 2:
    m &= df["发布日期"].between(pd.Timestamp(rng[0]), pd.Timestamp(rng[1]))
out = df[m].sort_values("发布日期", ascending=False)
st.markdown(f"**共 {len(out)} 条**")
st.dataframe(out, hide_index=True, width="stretch",
             column_config={"原文链接": st.column_config.LinkColumn("原文链接"),
                            "发布日期": st.column_config.DateColumn("发布日期")})
