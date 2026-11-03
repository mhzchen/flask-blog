# ruff: noqa: B023  # 递归闭包遍历 span 树（单次迭代内完成）
# -*- coding: utf-8 -*-
# 链路瀑布查看器（离线）：解析 otel-collector file exporter 落盘的 traces.json，
# 按 trace 分组渲染 HTTP->DB->Redis->Celery 调用链瀑布图，输出 reports/trace-report.html。
# 用法：venv\Scripts\python scripts\trace_report.py
import io
import json
import os

SRC = os.path.join("monitoring", "traces", "traces.json")
OUT = os.path.join("reports", "trace-report.html")


def load_spans():
    if not os.path.exists(SRC):
        return []
    text = io.open(SRC, encoding="utf-8").read().strip()
    if not text:
        return []
    data = None
    try:
        data = json.loads(text)
    except Exception:
        data = []
        for line in text.splitlines():
            line = line.strip()
            if line:
                try:
                    data.append(json.loads(line))
                except Exception:
                    pass
    spans = []
    for bundle in data or []:
        for rs in (bundle.get("resourceSpans") or []):
            for ss in (rs.get("scopeSpans") or []):
                for sp in (ss.get("spans") or []):
                    spans.append(sp)
    return spans


def build_traces(spans):
    traces = {}
    for sp in spans:
        tid = sp.get("traceId") or "?"
        traces.setdefault(tid, []).append(sp)
    result = []
    for tid, sps in traces.items():
        by_id = {}
        for sp in sps:
            by_id[sp.get("spanId")] = sp
        start = min((sp.get("startTimeUnixNano", 0) for sp in sps), default=0)
        end = max((sp.get("endTimeUnixNano", 0) for sp in sps), default=0)
        root = [sp for sp in sps if not sp.get("parentSpanId")]
        tree = []
        visited = set()

        def walk(sp, depth):
            sid = sp.get("spanId")
            if sid in visited:
                return
            visited.add(sid)
            s0 = sp.get("startTimeUnixNano", start) or start
            e0 = sp.get("endTimeUnixNano", s0) or s0
            tree.append({
                "name": sp.get("name", "?"),
                "depth": depth,
                "start": (s0 - start) / 1e6,
                "dur": (e0 - s0) / 1e6,
                "status": ((sp.get("status") or {}).get("code") or 0),
            })
            for child in sps:
                if child.get("parentSpanId") == sid:
                    walk(child, depth + 1)

        for sp in (root or [sps[0]]):
            walk(sp, 0)
        result.append({"trace": tid[:16], "spans": tree,
                       "total": (end - start) / 1e6, "count": len(sps)})
    result.sort(key=lambda t: t["count"], reverse=True)
    return result


def render(traces):
    if not traces:
        return ("# 链路瀑布报告\n\n暂无 trace 数据——otel-collector 未启动或网络不可达，"
                "span 未落盘。网络恢复后运行 `scripts\\monitoring-up.ps1` 并产生请求，再重跑本脚本。")
    lines = ["# 链路瀑布报告\n",
             f"共 {len(traces)} 条 trace（按 span 数排序）\n"]
    for t in traces:
        lines.append(f"## Trace `{t['trace']}` · {t['count']} spans · 总时长 {t['total']:.1f}ms\n")
        for s in t["spans"]:
            indent = "&nbsp;&nbsp;" * s["depth"]
            color = "#e74c3c" if s["status"] and s["status"] != 1 else "#2c9e5f"
            bar = min(100.0, (s["dur"] / (t["total"] or 1)) * 100)
            lines.append(
                f'<div style="font-family:monospace;font-size:12px;line-height:1.5">'
                f'{indent}<b style="color:{color}">{s["name"]}</b> '
                f'<span style="color:#888">+{s["start"]:.1f}ms · {s["dur"]:.1f}ms</span>'
                f'<span style="display:inline-block;background:{color};opacity:.35;'
                f'width:{bar:.0f}%;height:6px;vertical-align:middle;margin-left:6px"></span></div>')
        lines.append("\n")
    return "\n".join(lines)


def main():
    spans = load_spans()
    traces = build_traces(spans)
    os.makedirs("reports", exist_ok=True)
    body = render(traces)
    html_doc = ("<!doctype html><html lang=zh><meta charset=utf-8>"
                "<title>链路瀑布报告</title><body style='max-width:900px;margin:24px auto;padding:0 16px'>"
                + body + "</body></html>")
    io.open(OUT, "w", encoding="utf-8", newline="\n").write(html_doc)
    print(f"spans={len(spans)} traces={len(traces)} -> {OUT}")


if __name__ == "__main__":
    main()
