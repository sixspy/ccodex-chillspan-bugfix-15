"""一次性生成 12-chillspan 母仓业务文件（生成后勿重复覆盖 frontend 手改）。"""
from __future__ import annotations

import textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def w(rel: str, content: str) -> None:
    path = ROOT / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(content).lstrip("\n"), encoding="utf-8")


def main() -> None:
    emit_infra()
    emit_db()
    emit_models_validators_auth_locks()
    emit_services()
    emit_app()
    emit_fixtures()
    emit_tests()
    emit_frontend()
    print("emit done:", ROOT)


def emit_infra() -> None:
    w(
        "Dockerfile",
        """
        FROM python:3.12-slim
        WORKDIR /app
        COPY requirements.txt .
        RUN pip install --no-cache-dir -i https://pypi.tuna.tsinghua.edu.cn/simple --trusted-host pypi.tuna.tsinghua.edu.cn -r requirements.txt
        COPY backend/ ./backend/
        COPY frontend/ ./frontend/
        COPY fixtures/ ./fixtures/
        COPY tests/ ./tests/
        COPY pytest.ini .
        RUN mkdir -p /app/data
        ENV PYTHONUNBUFFERED=1
        EXPOSE 8000
        CMD ["python", "-m", "uvicorn", "app:app", "--app-dir", "backend", "--host", "0.0.0.0", "--port", "8000"]
        """,
    )
    w(
        "docker-compose.yml",
        """
        name: chillspan
        services:
          app:
            build: .
            ports:
              - "11400:8000"
            volumes:
              - ./data:/app/data
            healthcheck:
              test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health')"]
              interval: 5s
              timeout: 5s
              retries: 12
        """,
    )
    w(
        "requirements.txt",
        """
        fastapi>=0.110
        uvicorn[standard]>=0.27
        pydantic>=2
        pytest>=8
        httpx>=0.27
        """,
    )
    w(
        "pytest.ini",
        """
        [pytest]
        testpaths = tests
        pythonpath = backend
        """,
    )
    w(
        ".gitignore",
        """
        __pycache__/
        .pytest_cache/
        data/*.db
        .venv/
        """,
    )
    w("data/.gitkeep", "")
    w("backend/__init__.py", '"""冷链温谱管道母仓。"""\n')


if __name__ == "__main__":
    main()