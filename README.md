# 冷链温谱管道（12-chillspan）

冷链物流/仓储温控数据工程母仓：探头批次入库 → 超温游标闭环 → 封批升代 → 温谱导出 → 冷链血缘对账。

## 技术栈

- FastAPI + SQLite
- Vue 3 CDN SPA（深青监控台 UI）
- Docker 单服务一键起

## 账号

- `admin` / `123456`（写权限）
- `ops` / `123456`（ clerk 写）
- `viewer` / `123456`（只读）

## Docker 一键起

```bash
cd projects/12-chillspan
docker compose up -d --build
```

浏览器访问 http://localhost:11400

## 本机开发

```bash
cd projects/12-chillspan
pip install -r requirements.txt
cd backend
python -m uvicorn app:app --reload --host 127.0.0.1 --port 8000
```

前端静态文件由 FastAPI 挂载在根路径与 `/static`。

## 自检

```bash
python scripts/count_loc.py
pytest -q
node --check frontend/js/app.js
```