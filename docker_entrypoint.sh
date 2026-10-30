#!/bin/sh
# Flask 后端容器入口：
#   1) 等待 MySQL 就绪
#   2) 用 Alembic (flask db) 管理表结构：
#      - 全新数据库：flask db upgrade 建表 + seed 补数据
#      - 已有表但无迁移记录：先 flask db stamp head 认领，再 upgrade
#      - 已有迁移记录：直接 upgrade
#   3) 启动 gunicorn
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

echo "==> 检查数据库表状态 ..."
TABLES=$(python - <<'PY'
import os
from sqlalchemy import create_engine, inspect
url = os.environ["DATABASE_URL"]
engine = create_engine(url)
print(','.join(inspect(engine).get_table_names()))
PY
)

if [ -z "$TABLES" ]; then
    # 全新数据库：跑迁移建表，再插入测试数据
    echo "==> 全新数据库，执行 flask db upgrade 建表 ..."
    flask --app wsgi db upgrade
    echo "==> 插入测试数据 ..."
    python seed.py
else
    if echo "$TABLES" | grep -q "alembic_version"; then
        echo "==> 数据库已有迁移记录，执行 flask db upgrade ..."
        flask --app wsgi db upgrade
    else
        echo "==> 已有表但无迁移记录，标记为已迁移（stamp head）..."
        flask --app wsgi db stamp head
        flask --app wsgi db upgrade
    fi
fi

echo "==> 启动 gunicorn (0.0.0.0:8000) ..."
exec gunicorn --bind 0.0.0.0:8000 --workers 2 --timeout 60 wsgi:app