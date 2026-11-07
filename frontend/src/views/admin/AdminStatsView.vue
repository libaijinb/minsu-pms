<script setup>
import { onMounted, ref } from 'vue'
import { getStats } from '../../api/core'

/**
 * 经营统计：OCC / ADR / RevPAR 六个月趋势 + 渠道占比（BR-RPT-01/02）。
 * 图表用轻量 SVG 手绘（不引 ECharts，保持依赖精简）。
 */
const trend = ref([])
const channels = ref([])
const loading = ref(false)

const channelLabel = { self: '自营', meituan: '美团', tujia: '途家' }

// 折线图路径：把 [0,100] 的百分比映射到 SVG 坐标
function linePath(key) {
  const pts = trend.value.map((t, i) => {
    const x = 40 + (i * 460) / Math.max(1, trend.value.length - 1)
    const y = 160 - (t[key] / 100) * 140  // occ 是百分比
    return `${x},${y}`
  })
  return `M${pts.join(' L')}`
}

// ADR/RevPAR 是金额，各自按最大值归一化
function moneyPath(key) {
  const max = Math.max(1, ...trend.value.map((t) => t[key]))
  const pts = trend.value.map((t, i) => {
    const x = 40 + (i * 460) / Math.max(1, trend.value.length - 1)
    const y = 160 - (t[key] / max) * 140
    return `${x},${y}`
  })
  return `M${pts.join(' L')}`
}

async function loadData() {
  loading.value = true
  try {
    const data = await getStats()
    trend.value = data.trend || []
    channels.value = data.channels || []
  } finally {
    loading.value = false
  }
}

onMounted(loadData)
</script>

<template>
  <div v-loading="loading" class="page">
    <h2 class="page-title">经营统计</h2>

    <!-- 指标卡：取最近一个月 -->
    <div class="kpi-grid">
      <div v-for="t in trend.slice(-1)" :key="t.month" class="kpi-card">
        <span class="kpi-label">{{ t.month }} 出租率</span>
        <span class="kpi-value brand">{{ t.occ }}%</span>
      </div>
      <div v-for="t in trend.slice(-1)" :key="'adr' + t.month" class="kpi-card">
        <span class="kpi-label">平均每日房价 ADR</span>
        <span class="kpi-value">¥{{ t.adr }}</span>
      </div>
      <div v-for="t in trend.slice(-1)" :key="'revpar' + t.month" class="kpi-card">
        <span class="kpi-label">每间可售房收入 RevPAR</span>
        <span class="kpi-value">¥{{ t.revpar }}</span>
      </div>
    </div>

    <!-- 趋势图（SVG 手绘双折线：OCC 与 ADR） -->
    <div class="card chart-card">
      <h3>近 6 个月趋势</h3>
      <svg viewBox="0 0 540 200" class="chart">
        <!-- 网格线 -->
        <line v-for="y in [20, 60, 100, 140, 160]" :key="y" :x1="40" :y1="y" :x2="500" :y2="y" stroke="#f0f0f0" />
        <!-- OCC 折线（百分比） -->
        <path v-if="trend.length" :d="linePath('occ')" fill="none" stroke="#f6544a" stroke-width="2.5" />
        <!-- ADR 折线（金额归一化） -->
        <path v-if="trend.length" :d="moneyPath('adr')" fill="none" stroke="#3b82f6" stroke-width="2" stroke-dasharray="5 4" />
        <!-- 数据点 + 月份标签 -->
        <g v-for="(t, i) in trend" :key="t.month">
          <circle :cx="40 + (i * 460) / Math.max(1, trend.length - 1)"
            :cy="160 - (t.occ / 100) * 140" r="3.5" fill="#f6544a" />
          <text :x="40 + (i * 460) / Math.max(1, trend.length - 1)" y="185"
            text-anchor="middle" font-size="11" fill="#6b7280">{{ t.month.slice(2) }}</text>
        </g>
      </svg>
      <div class="chart-legend">
        <span><i class="line-dot occ"></i>出租率 OCC（%）</span>
        <span><i class="line-dot adr"></i>ADR（元，归一化）</span>
      </div>
    </div>

    <!-- 渠道占比 -->
    <div class="card">
      <h3>渠道订单占比</h3>
      <div v-if="channels.length" class="channel-rows">
        <div v-for="c in channels" :key="c.channel" class="channel-row">
          <span class="channel-name">{{ channelLabel[c.channel] || c.channel }}</span>
          <div class="channel-bar">
            <div class="bar-fill" :style="{ width: (c.cnt / Math.max(...channels.map(x => x.cnt)) * 100) + '%' }" />
          </div>
          <span class="channel-count">{{ c.cnt }} 单</span>
        </div>
      </div>
      <el-empty v-else description="暂无订单数据" :image-size="60" />
    </div>
  </div>
</template>

<style scoped>
.page-title {
  font-size: 18px;
  font-weight: 700;
  margin-bottom: 16px;
}

.kpi-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 14px;
  margin-bottom: 16px;
}
.kpi-card {
  background: #fff;
  border-radius: 14px;
  box-shadow: var(--shadow);
  padding: 18px 20px;
}
.kpi-label {
  display: block;
  font-size: 13px;
  color: var(--ink-2);
}
.kpi-value {
  display: block;
  font-size: 28px;
  font-weight: 800;
  margin-top: 6px;
}
.kpi-value.brand {
  color: var(--brand);
}

.card {
  background: #fff;
  border-radius: 14px;
  box-shadow: var(--shadow);
  padding: 20px;
  margin-bottom: 16px;
}
.card h3 {
  font-size: 15px;
  margin-bottom: 12px;
}

.chart {
  width: 100%;
  height: auto;
}
.chart-legend {
  display: flex;
  gap: 20px;
  font-size: 12px;
  color: var(--ink-2);
  margin-top: 8px;
}
.line-dot {
  display: inline-block;
  width: 16px;
  height: 3px;
  border-radius: 2px;
  margin-right: 6px;
  vertical-align: 3px;
}
.line-dot.occ {
  background: #f6544a;
}
.line-dot.adr {
  background: #3b82f6;
}

.channel-rows {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.channel-row {
  display: flex;
  align-items: center;
  gap: 12px;
}
.channel-name {
  width: 48px;
  font-size: 13px;
  color: var(--ink-2);
}
.channel-bar {
  flex: 1;
  height: 14px;
  background: #f3f4f6;
  border-radius: 999px;
  overflow: hidden;
}
.bar-fill {
  height: 100%;
  background: linear-gradient(90deg, var(--brand), #ff8a5b);
  border-radius: 999px;
  transition: width 0.4s;
}
.channel-count {
  width: 60px;
  text-align: right;
  font-size: 13px;
  font-weight: 600;
}
</style>
