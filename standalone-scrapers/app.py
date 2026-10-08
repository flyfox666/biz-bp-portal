"""入口：streamlit run app.py    多页面：总览 / 链家 / 统计局 / 政策"""
import streamlit as st

st.set_page_config(page_title="房地产数据抓取工具", layout="wide")
pg = st.navigation([
    st.Page("ui/home.py", title="总览", icon="🏠", default=True),
    st.Page("ui/lianjia.py", title="链家二手房", icon="🏘️"),
    st.Page("ui/nbs.py", title="统计局房价指数", icon="📈"),
    st.Page("ui/policy.py", title="房地产政策", icon="📜"),
])
pg.run()
