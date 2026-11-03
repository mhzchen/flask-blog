# ruff: noqa: E501  # SQL 基线行长
"""数据库巡检：EXPLAIN 基线 + 冗余索引检测 + 从库一致性校验。

用法：
    venv\\Scripts\\python scripts\\db_audit.py [--slave <from-url>]

- 不传 --slave：仅对主库做 EXPLAIN 基线与索引审查；
- 传 --slave：额外对比主/从关键表行数（读写分离一致性校验）。

输出：终端汇总 + 报告写入 reports/db-audit.md（UTF-8）。
"""
from __future__ import annotations

import io
import os
import sys
from typing import Any

from sqlalchemy import create_engine, text

DEFAULT_DSN = os.environ.get(
    "DATABASE_URL", "mysql+pymysql://root:root@localhost:3307/flask_blog?charset=utf8mb4"
)

# 对应 app 关键查询模式的 EXPLAIN 基线集（与 repositories/services 查询保持一致）
EXPLAIN_QUERIES: list[tuple[str, str]] = [
    ("列表-offset分页", "SELECT p.* FROM posts p ORDER BY p.created_at DESC LIMIT 6 OFFSET 0"),
    ("列表-keyset游标", "SELECT p.* FROM posts p WHERE (p.created_at, p.id) < ('2026-01-01 00:00:00', 9999) ORDER BY p.created_at DESC, p.id DESC LIMIT 6"),
    ("详情-主键", "SELECT * FROM posts WHERE id = 1"),
    ("分类筛选", "SELECT p.* FROM posts p WHERE p.category_id = 1 ORDER BY p.created_at DESC LIMIT 6"),
    ("全文搜索", "SELECT * FROM posts WHERE MATCH (title, summary, content) AGAINST ('flask' IN NATURAL LANGUAGE MODE)"),
    ("评论列表", "SELECT * FROM comments WHERE post_id = 1 ORDER BY created_at DESC"),
    ("点赞反查", "SELECT * FROM post_likes WHERE post_id = 1"),
]


def _show_indexes(c: Any) -> dict[str, list[dict]]:
    """收集所有表的索引结构：{table: [ {name, cols, nonunique, type} ]}。"""
    out: dict[str, list[dict]] = {}
    rows = c.execute(text(
        "SELECT TABLE_NAME, INDEX_NAME, COLUMN_NAME, SEQ_IN_INDEX, NON_UNIQUE, INDEX_TYPE "
        "FROM information_schema.statistics "
        "WHERE table_schema = DATABASE() ORDER BY TABLE_NAME, INDEX_NAME, SEQ_IN_INDEX"
    )).fetchall()
    for r in rows:
        t = r[0]
        out.setdefault(t, [])
        rec = next((x for x in out[t] if x["name"] == r[1]), None)
        if rec is None:
            rec = {"name": r[1], "cols": [], "nonunique": r[4], "type": r[5]}
            out[t].append(rec)
        rec["cols"].append(r[2])
    return out


def _row_counts(c: Any) -> dict[str, int]:
    rows = c.execute(text("SHOW TABLES")).fetchall()
    return {r[0]: c.execute(text(f"SELECT COUNT(*) FROM `{r[0]}`")).scalar() for r in rows}


def _explain(c: Any) -> list[dict]:
    out = []
    for label, sql in EXPLAIN_QUERIES:
        plan = c.execute(text("EXPLAIN " + sql)).fetchall()
        out.append({"label": label, "plan": [list(r) for r in plan]})
    return out


def _redundant_indexes(indexes: dict[str, list[dict]]) -> list[dict]:
    """按规则检测冗余索引：FULLTEXT 列集合被另一 FULLTEXT 覆盖。"""
    finds = []
    for table, idxs in indexes.items():
        fts = [i for i in idxs if i["type"] == "FULLTEXT"]
        for i in idxs:
            if i["type"] != "FULLTEXT":
                continue
            for j in fts:
                if j is i:
                    continue
                if set(i["cols"]) <= set(j["cols"]):
                    finds.append({
                        "table": table,
                        "index": i["name"],
                        "covered_by": j["name"],
                        "note": "FULLTEXT 列集合被更大 FULLTEXT 覆盖，属冗余",
                    })
    return finds


def _audit(dsn: str, label: str) -> dict:
    eng = create_engine(dsn)
    result: dict[str, Any] = {}
    with eng.connect() as c:
        result["label"] = label
        result["counts"] = _row_counts(c)
        result["indexes"] = _show_indexes(c)
        result["explain"] = _explain(c)
        result["redundant"] = _redundant_indexes(result["indexes"])
    eng.dispose()
    return result


def _slave_consistency(master: dict, slave: dict) -> list[dict]:
    diffs = []
    for table, m in master["counts"].items():
        s = slave["counts"].get(table, "N/A")
        if s != m:
            diffs.append({"table": table, "master": m, "slave": s})
    return diffs


def _fmt_plan(plan: list[list]) -> str:
    if not plan:
        return "  (无输出)"
    lines = []
    for row in plan:
        lines.append("  " + " | ".join(str(x) for x in row[:8]))
    return "\n".join(lines)


def _build_report(master: dict, slave: dict | None, consistency: list[dict]) -> str:
    L: list[str] = []
    L.append("# 数据库巡检报告\n")
    L.append(f"巡检对象：**{master['label']}**" + (f" + **{slave['label']}**" if slave else "") + "\n")
    L.append("## 表与行数\n")
    L.append("| 表 | 行数 |")
    L.append("|---|--:|")
    for t, n in sorted(master["counts"].items()):
        L.append(f"| `{t}` | {n} |")
    L.append("\n## 索引清单（冗余项 ★）\n")
    red = {(r["table"], r["index"]) for r in master["redundant"]}
    for t, idxs in sorted(master["indexes"].items()):
        for i in idxs:
            star = " ★冗余" if (t, i["name"]) in red else ""
            L.append(f"- `{t}`.**{i['name']}** 列={i['cols']} 唯一={'否' if i['nonunique'] else '是'} 类型={i['type']}{star}")
    L.append("\n## 冗余索引检测\n")
    if master["redundant"]:
        for r in master["redundant"]:
            L.append(f"- `{r['table']}`.**{r['index']}** 被 `{r['covered_by']}` 覆盖 → 建议删除（{r['note']}）")
    else:
        L.append("- 未发现被完全覆盖的 FULLTEXT 冗余索引。")
    L.append("\n## EXPLAIN 基线\n")
    for e in master["explain"]:
        L.append(f"### {e['label']}\n```\n{_fmt_plan(e['plan'])}\n```\n")
    L.append("## 从库一致性\n")
    if slave is None:
        L.append("- 未配置从库（无 `DATABASE_URL_SLAVE`），当前为单库模式，无一致性校验对象；配好从库后以 `--slave` 重跑本脚本即可对比各表行数。")
    elif consistency:
        L.append("- 发现主从行数不一致：\n")
        for d in consistency:
            L.append(f"  - `{d['table']}`：主 {d['master']} / 从 {d['slave']}")
    else:
        L.append("- 主从各表行数一致。")
    return "\n".join(L) + "\n"


def main() -> None:
    slave_dsn: str | None = None
    if "--slave" in sys.argv:
        slave_dsn = sys.argv[sys.argv.index("--slave") + 1]
    master = _audit(DEFAULT_DSN, "主库")
    slave = _audit(slave_dsn, "从库") if slave_dsn else None
    consistency = _slave_consistency(master, slave) if slave else []

    print(f"表：{len(master['counts'])} 张；冗余 FULLTEXT 索引：{len(master['redundant'])} 个")
    for r in master["redundant"]:
        print(f"  ★ {r['table']}.{r['index']} → 被 {r['covered_by']} 覆盖")

    report = _build_report(master, slave, consistency)
    os.makedirs("reports", exist_ok=True)
    io.open("reports/db-audit.md", "w", encoding="utf-8", newline="\n").write(report)
    print("报告已写入 reports/db-audit.md")


if __name__ == "__main__":
    main()
