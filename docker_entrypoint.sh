#!/bin/sh
# Flask 后端容器入口：
#   1) 等待 MySQL 就绪
#   2) 若数据库为空（无表）则执行 seed.py 建表 + 插入测试数据
#   3) 启动 gunicorn
# 说明：seed.py 内部会 drop_all()，所以只在“没有任何表”时执行，避免每次重启清空数据。
set -e

echo "==> 等待 MySQL 就绪 ..."
python - <<'PY'
import os, time
from sqlalchemy import create_engine, text

url = os.environ.get("DATABASE_URL", "")
if not url:
    raise SystemExit("缺少环境变量 DATABASE_URL")
engine = create_engine(url, pool_pre_ping=True)
for _ in range(60):
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print("MySQL 就绪")
        break
    except Exception:
        time.sleep(1)
else:
    raise SystemExit("MySQL 在 60s 内未就绪")
PY

echo "==> 检查数据库是否为空 ..."
# 用 if 承接退出码：数据库已有表时 python 返回 1，set -e 不会把整个脚本杀掉
if python - <<'PY'
import os, sys
from sqlalchemy import create_engine, inspect
url = os.environ["DATABASE_URL"]
engine = create_engine(url)
tables = inspect(engine).get_table_names()
sys.exit(0 if not tables else 1)
PY
then
    echo "==> 首次启动，执行 seed.py 初始化数据库 ..."
    python seed.py
else
    echo "==> 数据库已有表，跳过 seed"
fi

echo "==> 启动 gunicorn (0.0.0.0:8000) ..."
exec gunicorn --bind 0.0.0.0:8000 --workers 2 --timeout 60 wsgi:app
