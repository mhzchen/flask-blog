"""轻量压测脚本（无第三方依赖）。

用多线程并发请求目标接口，统计吞吐 / 延迟分布 / 错误率，
作为性能基线。用法：
    python scripts/load_test.py --url http://localhost:8000/api/posts --concurrency 20 --total 500
默认参数覆盖两个热点场景：
    /api/posts          (Redis 缓存命中路径)
    /api/posts/1        (DB 直查路径，无缓存)
"""
import argparse
import threading
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor


def _hit(url: str) -> tuple[float, int]:
    """发一次请求，返回 (耗时秒, HTTP状态码)。"""
    start = time.perf_counter()
    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            return time.perf_counter() - start, resp.status
    except urllib.error.HTTPError as e:
        return time.perf_counter() - start, e.code
    except Exception:
        return time.perf_counter() - start, 0  # 0 表示网络/超时错误


def run(url: str, concurrency: int, total: int, warmup: int = 20):
    """并发压测：先 warmup 若干请求预热缓存，再统计。"""
    # 预热（让 Redis 缓存命中进入稳态）
    for _ in range(warmup):
        _hit(url)
    latencies: list[float] = []
    errors = 0
    lock = threading.Lock()
    done = 0

    def worker(_):
        nonlocal errors, done
        lat, code = _hit(url)
        with lock:
            done += 1
            if code != 200:
                errors += 1
            else:
                latencies.append(lat)

    start = time.perf_counter()
    with ThreadPoolExecutor(max_workers=concurrency) as ex:
        list(ex.map(worker, range(total)))
    elapsed = time.perf_counter() - start

    qps = total / elapsed
    latencies.sort()
    n = len(latencies)
    p50 = latencies[int(n * 0.5) - 1] * 1000 if n else 0
    p95 = latencies[int(n * 0.95) - 1] * 1000 if n else 0
    p99 = latencies[int(n * 0.99) - 1] * 1000 if n else 0
    avg = (sum(latencies) / n * 1000) if n else 0
    err_rate = errors / total * 100

    print(f"\n=== {url} ===")
    print(f"并发 {concurrency}，总量 {total}，耗时 {elapsed:.2f}s")
    print(f"吞吐 QPS: {qps:.0f}")
    print(f"延迟: avg {avg:.1f}ms | p50 {p50:.1f}ms | p95 {p95:.1f}ms | p99 {p99:.1f}ms")
    print(f"错误: {errors}/{total} ({err_rate:.2f}%)")
    return {"url": url, "qps": qps, "avg": avg, "p50": p50, "p95": p95, "p99": p99, "err_rate": err_rate}


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="轻量压测基线")
    ap.add_argument("--url", default="http://localhost:8000/api/posts", help="目标 URL")
    ap.add_argument("--concurrency", type=int, default=20, help="并发数")
    ap.add_argument("--total", type=int, default=500, help="总请求数")
    args = ap.parse_args()
    run(args.url, args.concurrency, args.total)
