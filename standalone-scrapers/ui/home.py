"""总览页：三个数据源的最新状态 + 一键下载全部。"""
import io
from datetime import datetime

import streamlit as st

from scraper_kit.runner import build_workbook
from ui import common as C

st.title("房地产数据抓取工具")
st.caption("数据来源：国家统计局、链家（挂牌）、住建部。在左侧选择页面，各页面有自己的抓取与筛选条件。")
st.warning("链家价格为**挂牌价，不是成交价**；红色“兜底数据”是演示用假数据，**不能当真实数据使用**。")

state = C._state()["cache"]
cols = st.columns(len(C.SCRAPERS))
latest = []
for col, (sid, s) in zip(cols, C.SCRAPERS.items()):
    entries = [v for k, v in state.items() if k[0] == sid]
    res = max(entries, key=lambda r: r["at"]) if entries else None
    with col:
        st.subheader(C.SHORT_NAME[sid])
        if res is None:
            st.write("暂无数据")
        else:
            latest.append(res)
            st.write(f"{len(res['rows'])} 行 · {C.fmt_time(res['at'])}")
            (st.error if res["fallback"] else st.success)("兜底数据" if res["fallback"] else "实时数据")

if latest:
    buf = io.BytesIO()
    build_workbook(latest).save(buf)
    st.download_button("下载全部最新结果 (Excel)", buf.getvalue(),
                       file_name=f"房地产数据_{datetime.now():%Y%m%d_%H%M}.xlsx",
                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
else:
    st.info("还没有人抓取过数据，请到左侧页面开始。")
