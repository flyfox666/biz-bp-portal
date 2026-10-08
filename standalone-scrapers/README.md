# 房地产数据抓取工具（独立版）

三个爬虫：国家统计局 70 城房价指数 / 链家二手房挂牌 / 住建部政策。
来自 InsightBP 项目，已去掉数据库依赖，可单独运行。

## 本地运行

```
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt      # Linux/Mac: .venv/bin/pip
.venv\Scripts\streamlit run app.py                 # 网页版，浏览器打开 http://localhost:8501
.venv\Scripts\python run_demo.py                   # 命令行版，输出 output/*.xlsx
```

## 页面

左侧导航四个页面，各有自己的抓取与筛选条件：

- **总览**：三个数据源最新状态、一键下载全部。
- **链家二手房**：上方"抓取条件"（城市）决定请求；下方"结果筛选"（区域、户型、朝向、装修、楼型、楼层、建成年份、总价/面积区间、关键词）在本地过滤，**不产生新请求**；附平均/中位数单价和区域对比图。
- **统计局房价指数**：城市、新房/二手、同比/环比，涨跌排行。
- **房地产政策**：关键词、级别、城市、日期范围，原文链接可点击。

## 降低触发反爬风险的设计

1. 缓存优先：打开页面只展示已有结果，不自动抓取；同条件 30 分钟内复用。
2. 排队：同一时刻只有一个真实抓取，其他人等待后直接命中缓存。
3. 冷却：同一数据源两次真实抓取至少间隔 60 秒。
4. 筛选尽量放在本地，不增加请求。

## 重要说明

- 实时抓取失败时会退回**兜底(mock)数据**，网页和 Excel 里都会明确标注，**不能当真实数据用**。
- 链家数据是**挂牌价，不是成交价**；每个城市只抓列表第 1 页（约 30 套），是样本不是全量。
- 链家城市代码（如 cd=成都）未逐一验证，抓不到时会显示为兜底数据。
- 链家明细字段（户型、面积、朝向等）按页面结构解析，仅用模拟页面验证过，真实页面结构以你本地实测为准。

## 部署到云服务器（给同事用）

1. 服务器装 Python 3.10+，拉代码，按上面创建 venv 并安装依赖。
2. 后台运行：`streamlit run app.py --server.port 8501 --server.address 127.0.0.1`
   （可用 systemd 或 supervisor 守护）。
3. 用 Nginx/Caddy 反向代理到你的域名并配 HTTPS，**必须开启 WebSocket 转发**
   （Nginx: `proxy_set_header Upgrade $http_upgrade; proxy_set_header Connection "upgrade";`）。
4. **加访问控制**：Streamlit 自带没有登录。最简单的是在 Nginx 加 Basic Auth
   （`auth_basic` + `htpasswd`），或用 Cloudflare Access 等；不要裸露在公网。
5. 注意：云服务器的 IP 抓链家更容易被反爬拦截（机房 IP 常被识别），效果以实测为准。
