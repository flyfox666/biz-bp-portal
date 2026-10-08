"""统计局 70 城房价指数页。"""
import pandas as pd
import streamlit as st

from scraper_kit.runner import to_records
from ui import common as C

SID = "nbs_house_price"
st.title("统计局 70 城房价指数")
st.caption("指数以上年同月或上月为基期，100 为基准；这里展示的是同比、环比涨跌幅(%)。")

if st.button("开始抓取", type="primary"):
    C.do_fetch(SID)
result = C.peek(SID)
C.render_status(result, st.session_state.get(f"cached_{SID}"))
if result is None or not result["rows"]:
    st.stop()

cols, rows = to_records(result)
df = pd.DataFrame(rows, columns=cols)
if result["fallback"]:
    st.warning("以下为兜底数据（仅少数城市），仅用于演示格式。")

with st.container(border=True):
    a, b, c = st.columns(3)
    cities = a.multiselect("城市", sorted(df["城市"].dropna().unique()))
    kind = b.radio("房屋类型", ["新建商品住宅", "二手住宅"], horizontal=True)
    basis = c.radio("口径", ["同比", "环比"], horizontal=True)
metric = f"{kind}{basis}(%)"
view = df[df["城市"].isin(cities)] if cities else df
view = view[["城市", "期间", metric]].dropna(subset=[metric]).sort_values(metric, ascending=False)

st.markdown(f"**{metric} 排行**")
if view.empty:
    st.info("当前条件下没有数据。")
else:
    st.bar_chart(view.set_index("城市")[metric])
    st.dataframe(view, hide_index=True, width="stretch")
with st.expander("全部字段"):
    st.dataframe(df, hide_index=True, width="stretch")
