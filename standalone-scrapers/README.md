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

## 重要说明

- 实时抓取失败时会退回**兜底(mock)数据**，网页和 Excel 里都会明确标注，**不能当真实数据用**。
- 链家数据是**挂牌价，不是成交价**；每个城市只抓列表第 1 页（约 30 套），是样本不是全量。
- 链家城市代码（如 cd=成都）未逐一验证，抓不到时会显示为兜底数据。
- 同样条件 30 分钟内复用缓存结果，所有访问者共享，避免重复请求触发反爬。

## 部署到云服务器（给同事用）

1. 服务器装 Python 3.10+，拉代码，按上面创建 venv 并安装依赖。
2. 后台运行：`streamlit run app.py --server.port 8501 --server.address 127.0.0.1`
   （可用 systemd 或 supervisor 守护）。
3. 用 Nginx/Caddy 反向代理到你的域名并配 HTTPS，**必须开启 WebSocket 转发**
   （Nginx: `proxy_set_header Upgrade $http_upgrade; proxy_set_header Connection "upgrade";`）。
4. **加访问控制**：Streamlit 自带没有登录。最简单的是在 Nginx 加 Basic Auth
   （`auth_basic` + `htpasswd`），或用 Cloudflare Access 等；不要裸露在公网。
5. 注意：云服务器的 IP 抓链家更容易被反爬拦截（机房 IP 常被识别），效果以实测为准。
