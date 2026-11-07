<script setup>
/**
 * 价格日历（民宿预订核心交互）：
 * - 展示连续多个月，每格显示日期 + 当晚价格 + 状态（可订/已订/锁定/关闭）
 * - 点击选入住日，再点选退房日；区间内必须全部可订，已订/锁定/关闭不可选
 * - 底部显示选中区间的晚数与总价（清洁费由后端订单接口计算，这里只报房费小计）
 */
import { computed, ref, watch } from 'vue'
import dayjs from 'dayjs'
import { getCalendar } from '../api/listings'

const props = defineProps({
  listingId: { type: [String, Number], required: true },
  months: { type: Number, default: 2 },  // 一次展示几个月
})
const emit = defineEmits(['range-change'])

const calendarMap = ref({})  // 'YYYY-MM-DD' -> {status, price}
const loading = ref(false)
const checkin = ref('')     // 'YYYY-MM-DD'
const checkout = ref('')

// 生成要展示的月份列表（从本月开始）
const monthList = computed(() => {
  const list = []
  for (let i = 0; i < props.months; i++) {
    list.push(dayjs().add(i, 'month'))
  }
  return list
})

const weekdays = ['日', '一', '二', '三', '四', '五', '六']

// 每月生成 6×7 网格（自然日顺序，含上下月补位）
function monthGrid(month) {
  const first = month.startOf('month')
  const start = first.subtract(first.day(), 'day')  // 回退到上周日
  const days = []
  for (let i = 0; i < 42; i++) {
    const d = start.add(i, 'day')
    days.push({
      date: d.format('YYYY-MM-DD'),
      day: d.date(),
      inMonth: d.month() === month.month(),
      past: d.isBefore(dayjs(), 'day'),
      ...(calendarMap.value[d.format('YYYY-MM-DD')] || { status: 'loading', price: 0 }),
    })
  }
  return days
}

async function loadCalendar() {
  loading.value = true
  try {
    const start = dayjs().format('YYYY-MM-DD')
    const end = dayjs().add(props.months, 'month').endOf('month').format('YYYY-MM-DD')
    const rows = await getCalendar(props.listingId, { start, end })
    calendarMap.value = Object.fromEntries(rows.map((r) => [r.date, { status: r.status, price: r.price }]))
  } finally {
    loading.value = false
  }
}

// 区间总价（房费小计，不含清洁费/服务费）
const rangeInfo = computed(() => {
  if (!checkin.value || !checkout.value) return null
  let total = 0
  let nights = 0
  let d = dayjs(checkin.value)
  const end = dayjs(checkout.value)
  while (d.isBefore(end)) {
    const cell = calendarMap.value[d.format('YYYY-MM-DD')]
    if (!cell || cell.status !== 'available') return null
    total += Number(cell.price)
    nights += 1
    d = d.add(1, 'day')
  }
  return { nights, total }
})

function onClickDay(cell) {
  if (cell.past || cell.status !== 'available') return
  const date = cell.date
  // 未选或已选完整区间 -> 重新开始选入住日
  if (!checkin.value || (checkin.value && checkout.value) || date <= checkin.value) {
    checkin.value = date
    checkout.value = ''
  } else {
    // 选了入住日后再点：必须区间内全部可订
    let ok = true
    let d = dayjs(checkin.value)
    while (d.isBefore(dayjs(date))) {
      const c = calendarMap.value[d.format('YYYY-MM-DD')]
      if (!c || c.status !== 'available') { ok = false; break }
      d = d.add(1, 'day')
    }
    if (!ok) {
      checkin.value = date  // 区间不可订则把这次点击当作新的入住日
      checkout.value = ''
      return
    }
    checkout.value = date
  }
}

watch([checkin, checkout], () => {
  emit('range-change', { checkin: checkin.value, checkout: checkout.value, ...(rangeInfo.value || {}) })
})

watch(() => props.listingId, loadCalendar, { immediate: true })

// 暴露给父组件（预订卡需要读取当前选择）
defineExpose({ checkin, checkout, rangeInfo })
</script>

<template>
  <div v-loading="loading" class="price-calendar">
    <div class="months">
      <div v-for="(m, idx) in monthList" :key="idx" class="month">
        <h4 class="month-title">{{ m.format('YYYY 年 M 月') }}</h4>
        <div class="weekdays">
          <span v-for="w in weekdays" :key="w">{{ w }}</span>
        </div>
        <div class="days">
          <div v-for="cell in monthGrid(m)" :key="cell.date" class="day"
            :class="{
              'out-month': !cell.inMonth,
              past: cell.past,
              available: cell.status === 'available' && !cell.past,
              booked: cell.status === 'booked',
              locked: cell.status === 'locked' || cell.status === 'closed',
              'is-checkin': cell.date === checkin,
              'is-checkout': cell.date === checkout,
              'in-range': checkin && checkout && cell.date > checkin && cell.date < checkout,
            }"
            @click="onClickDay(cell)">
            <span class="d-num">{{ cell.day }}</span>
            <span v-if="cell.status === 'available' && !cell.past" class="d-price">¥{{ cell.price }}</span>
            <span v-else-if="cell.status === 'booked'" class="d-tag">已订</span>
            <span v-else-if="cell.status === 'locked' || cell.status === 'closed'" class="d-tag">关</span>
          </div>
        </div>
      </div>
    </div>

    <div class="legend">
      <span><i class="dot available"></i>可订</span>
      <span><i class="dot booked"></i>已订</span>
      <span><i class="dot locked"></i>关闭/锁定</span>
      <span v-if="rangeInfo" class="range-summary">
        已选 {{ rangeInfo.nights }} 晚 · 房费小计 <b>¥{{ rangeInfo.total }}</b>
      </span>
    </div>
  </div>
</template>

<style scoped>
.months {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 24px;
}

.month-title {
  font-size: 15px;
  font-weight: 700;
  margin-bottom: 8px;
}

.weekdays,
.days {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  gap: 4px;
}

.weekdays span {
  text-align: center;
  font-size: 12px;
  color: var(--ink-2);
  padding: 4px 0;
}

.day {
  aspect-ratio: 1;
  border-radius: 8px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 1px;
  font-size: 13px;
  cursor: default;
  user-select: none;
  border: 1px solid transparent;
}
.d-num {
  font-weight: 600;
}
.d-price {
  font-size: 10px;
  color: var(--ink-2);
}
.d-tag {
  font-size: 10px;
  color: #d1d5db;
}

.day.out-month {
  opacity: 0.35;
}
.day.past {
  color: #d1d5db;
}
.day.available {
  cursor: pointer;
  color: var(--ink);
  transition: background 0.15s, border-color 0.15s;
}
.day.available:hover {
  background: var(--brand-light);
  border-color: var(--brand);
}
.day.booked {
  background: #f3f4f6;
  color: #9ca3af;
  text-decoration: line-through;
}
.day.locked {
  background: repeating-linear-gradient(45deg, #f9fafb, #f9fafb 4px, #f3f4f6 4px, #f3f4f6 8px);
  color: #9ca3af;
}

/* 选中态：入住/退房日用品牌色实底，区间中间日用浅底 */
.day.is-checkin,
.day.is-checkout {
  background: var(--brand);
  color: #fff;
}
.day.is-checkin .d-price,
.day.is-checkout .d-price {
  color: rgba(255, 255, 255, 0.85);
}
.day.in-range {
  background: var(--brand-light);
  color: var(--brand-dark);
}

.legend {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-top: 16px;
  font-size: 12px;
  color: var(--ink-2);
  flex-wrap: wrap;
}
.dot {
  display: inline-block;
  width: 10px;
  height: 10px;
  border-radius: 3px;
  margin-right: 4px;
  vertical-align: -1px;
}
.dot.available {
  background: #fff;
  border: 1px solid var(--brand);
}
.dot.booked {
  background: #f3f4f6;
  border: 1px solid #d1d5db;
}
.dot.locked {
  background: repeating-linear-gradient(45deg, #f9fafb, #f9fafb 3px, #e5e7eb 3px, #e5e7eb 6px);
  border: 1px solid #e5e7eb;
}

.range-summary {
  margin-left: auto;
}
.range-summary b {
  color: var(--brand);
  font-size: 14px;
}

@media (max-width: 640px) {
  .months {
    grid-template-columns: 1fr;
  }
}
</style>
