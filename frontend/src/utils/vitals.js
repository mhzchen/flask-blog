// Web Vitals 本地聚合：把每次采集的指标写入 localStorage，供 /vitals 可视化页展示趋势。
const KEY = 'web_vitals_history'
const MAX = 40

export function recordVitals(metric) {
  try {
    const hist = loadHistory()
    hist.push({
      name: metric.name,
      value: Number(metric.value.toFixed(2)),
      rating: metric.rating,
      ts: Date.now(),
    })
    if (hist.length > MAX) hist.splice(0, hist.length - MAX)
    localStorage.setItem(KEY, JSON.stringify(hist))
  } catch (e) {
    // 隐私模式/存储受限时静默失败，不影响采集
  }
}

export function loadHistory() {
  try {
    return JSON.parse(localStorage.getItem(KEY) || '[]')
  } catch (e) {
    return []
  }
}

export function clearHistory() {
  try {
    localStorage.removeItem(KEY)
  } catch (e) {
    // 忽略
  }
}