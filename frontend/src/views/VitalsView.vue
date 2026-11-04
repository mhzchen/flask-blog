<script setup>
import { ref, computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { loadHistory, clearHistory } from '../utils/vitals'

const { t } = useI18n()
const entries = ref([])
const metricNames = ['LCP', 'FCP', 'INP', 'CLS', 'TTFB']
const w = 360
const max = 40

onMounted(() => { entries.value = loadHistory() })

function clear() { clearHistory(); entries.value = [] }

// 按指标分组，取最近 max 条
const groups = computed(() =>
  metricNames
    .map((name) => {
      const list = entries.value.filter((e) => e.name === name).slice(-max)
      return { name, list, latest: list[list.length - 1] || null }
    })
    .filter((g) => g.list.length > 0)
)

function avg(g) {
  return Math.round(g.list.reduce((s, e) => s + e.value, 0) / g.list.length)
}

// 简单折线点集（归一化到 viewBox 0..360 x 6..54）
function points(g) {
  if (g.list.length < 2) return ''
  const vals = g.list.map((e) => e.value)
  const lo = Math.min(...vals)
  const hi = Math.max(...vals)
  const range = hi - lo || 1
  const step = w / (g.list.length - 1)
  return g.list
    .map((e, i) => `${(i * step).toFixed(1)},${(54 - ((e.value - lo) / range) * 44).toFixed(1)}`)
    .join(' ')
}

const unit = (name) => (name === 'CLS' ? '' : ' ms')
</script>

<template>
  <div class="vitals">
    <h2>{{ t('vitals.title') }}</h2>
    <p class="desc">{{ t('vitals.desc') }}</p>
    <button v-if="groups.length" class="clear" @click="clear">{{ t('vitals.clear') }}</button>
    <p v-if="!groups.length" class="empty">{{ t('vitals.noData') }}</p>
    <div v-for="g in groups" :key="g.name" class="group">
      <h3>
        {{ g.name }}
        <span v-if="g.latest" :class="g.latest.rating">{{ g.latest.rating }}</span>
      </h3>
      <svg :viewBox="`0 0 ${w} 60`" class="chart" preserveAspectRatio="none" role="img" :aria-label="`${g.name} trend`">
        <polyline v-if="points(g)" :points="points(g)" fill="none" stroke="var(--primary)" stroke-width="2" />
      </svg>
      <div v-if="g.latest" class="stats">
        {{ t('vitals.latest') }} <b>{{ g.latest.value }}</b>{{ unit(g.name) }} · {{ t('vitals.avg') }} <b>{{ avg(g) }}</b>{{ unit(g.name) }} ·
        {{ t('vitals.total', { n: g.list.length }) }}
      </div>
    </div>
  </div>
</template>

<style scoped>
.vitals { max-width: 720px; margin: 0 auto; padding: 24px 16px; }
.desc { color: var(--muted-strong); font-size: 13px; line-height: 1.6; }
.group { margin-bottom: 20px; background: var(--card-bg); border: 1px solid var(--border); border-radius: 8px; padding: 14px 16px; }
h3 { display: flex; align-items: center; gap: 8px; margin: 0 0 10px; font-size: 15px; color: var(--heading); }
h3 span { font-size: 12px; padding: 2px 8px; border-radius: 10px; }
.good { background: var(--success-bg); color: #1a7f4b; }
.needs-improvement { background: #fff4e0; color: #b9760a; }
.poor { background: var(--danger-bg); color: #c0392b; }
.chart { width: 100%; height: 60px; display: block; }
.stats { margin-top: 6px; font-size: 13px; color: var(--muted-strong); }
.empty { color: var(--muted); font-size: 14px; }
.clear { border: 1px solid var(--border-strong); background: var(--card-bg); color: var(--fg); padding: 6px 14px; border-radius: 6px; cursor: pointer; margin: 4px 0 14px; }
</style>
