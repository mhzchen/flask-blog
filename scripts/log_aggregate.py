#!/usr/bin/env python
"""日志聚合查看器（#58）：把 logs/ 下按天滚动的 JSON 日志合并、过滤、统计。

结构化日志一行一条 JSON，落盘到 logs/app.log（LOG_FILE_ENABLED 时按天滚动，见 __init__._configure_logging）。
本脚本把多天/滚动日志合并，按条件过滤并输出，实现"日志聚合"查看（无需 ELK/Loki 即可本地集中排查）。

用法：
  python scripts/log_aggregate.py                       # 列出最近 200 条匹配日志
  python scripts/log_aggregate.py --level WARNING       # 只看 WARNING（含 degradation 事件）
  python scripts/log_aggregate.py --msg degradation     # 只看降级事件
  python scripts/log_aggregate.py --service celery      # 只看某服务的降级事件
  python scripts/log_aggregate.py --since 2026-11-03    # 只看该日期起的日志
  python scripts/log_aggregate.py --summary             # 按 logger/level/msg 统计汇总
  python scripts/log_aggregate.py --degradations        # 只列降级事件（含 service/reason）
"""
import argparse
import glob
import json
import os

DEFAULT_LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'logs')


def iter_records(log_dir):
    for pat in (os.path.join(log_dir, '*.log'), os.path.join(log_dir, '*.log.*')):
        for fp in sorted(glob.glob(pat)):
            try:
                with open(fp, encoding='utf-8') as fh:
                    for line in fh:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            rec = json.loads(line)
                        except Exception:
                            continue
                        if isinstance(rec, dict):
                            yield rec
            except Exception:
                continue


def _match(rec, level, msg, service, since):
    if level and rec.get('level', '').upper() != level.upper():
        return False
    if msg and msg.lower() not in rec.get('msg', '').lower():
        return False
    if service and rec.get('service', '') != service:
        return False
    if since and rec.get('ts', '') < since:
        return False
    return True


def main():
    ap = argparse.ArgumentParser(description='聚合查看 logs/ 下的结构化 JSON 日志')
    ap.add_argument('--log-dir', default=DEFAULT_LOG_DIR)
    ap.add_argument('--level', default=None, help='只看该级别（如 WARNING/ERROR/INFO）')
    ap.add_argument('--msg', default=None, help='只看 msg 包含该关键字的行（如 degradation）')
    ap.add_argument('--service', default=None, help='只看某服务的降级事件（如 celery/redis_cache）')
    ap.add_argument('--since', default=None, help='只看 ts >= 该前缀的日志（如 2026-11-03）')
    ap.add_argument('--summary', action='store_true', help='按 logger/level/msg 输出统计汇总')
    ap.add_argument('--degradations', action='store_true', help='只输出降级事件（含 service/reason）')
    ap.add_argument('--limit', type=int, default=200, help='列表模式最多输出行数（默认 200）')
    args = ap.parse_args()

    records = [r for r in iter_records(args.log_dir) if _match(r, args.level, args.msg, args.service, args.since)]
    if not records:
        print('no matching log records under %s' % args.log_dir)
        return

    if args.summary:
        from collections import Counter
        by_logger = Counter(r.get('logger', '') for r in records)
        by_level = Counter(r.get('level', '') for r in records)
        by_msg = Counter(r.get('msg', '') for r in records)
        print('== 按 logger ==')
        for k, v in by_logger.most_common():
            print('  %-24s %d' % (k, v))
        print('== 按 level ==')
        for k, v in by_level.most_common():
            print('  %-10s %d' % (k, v))
        print('== 按 msg ==')
        for k, v in by_msg.most_common():
            print('  %-28s %d' % (k, v))
        return

    rows = records
    if args.degradations:
        rows = [r for r in records if r.get('msg') == 'degradation']
        if not rows:
            print('no degradation events matched')
            return
        print('== degradation events (%d) ==' % len(rows))
        for r in rows[-args.limit:]:
            print('  %s | %s | %s | %s' % (
                r.get('ts', ''), r.get('service', ''), r.get('level', ''), r.get('reason', '')))
        return

    print('== matching logs (%d, showing last %d) ==' % (len(rows), min(args.limit, len(rows))))
    for r in rows[-args.limit:]:
        line = {'ts': r.get('ts'), 'level': r.get('level'), 'logger': r.get('logger'), 'msg': r.get('msg')}
        for k in ('service', 'reason', 'rid', 'method', 'path', 'status', 'dur_ms'):
            if r.get(k) is not None:
                line[k] = r.get(k)
        print(json.dumps(line, ensure_ascii=False))


if __name__ == '__main__':
    main()
