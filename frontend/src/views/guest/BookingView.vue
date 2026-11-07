<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { createOrder, payOrder, getOrder } from '../../api/orders'
import { getListing } from '../../api/listings'

/**
 * 确认下单页：
 * ① 从 query 带房源/日期/人数，展示金额明细（房费小计由后端快照计算）
 * ② 提交创建订单（占房在事务内完成，失败返回 409 冲突）
 * ③ 创建后直接模拟支付（真实环境由支付宝回调驱动）
 */
const route = useRoute()
const router = useRouter()

const listing = ref(null)
const submitting = ref(false)
const paying = ref(false)
const createdOrder = ref(null)

const ci = computed(() => route.query.ci)
const co = computed(() => route.query.co)
const guests = computed(() => Number(route.query.guests) || 1)
const nights = computed(() => {
  if (!ci.value || !co.value) return 0
  return Math.max(0, (new Date(co.value) - new Date(ci.value)) / 86400000)
})

// 金额明细取自后端订单快照（创建后），创建前只展示预估说明
const detail = computed(() => createdOrder.value?.amount_detail || null)
const total = computed(() => createdOrder.value?.total_amount ?? null)

async function loadListing() {
  listing.value = await getListing(route.params.id)
}

async function submitOrder() {
  if (!ci.value || !co.value) {
    ElMessage.warning('缺少日期信息，请从房源详情页进入')
    return
  }
  submitting.value = true
  try {
    const order = await createOrder({
      listing: Number(route.params.id),
      checkin_date: ci.value,
      checkout_date: co.value,
      guests_count: guests.value,
      channel: 'self',
    })
    createdOrder.value = order
    ElMessage.success('订单已创建，请完成支付')
  } catch {
    // 409 冲突等错误由拦截器提示
  } finally {
    submitting.value = false
  }
}

async function pay() {
  paying.value = true
  try {
    const order = await payOrder(createdOrder.value.order_no)
    createdOrder.value = order
    ElMessage.success('支付成功！等待房东确认')
    setTimeout(() => router.push('/my/orders'), 1200)
  } finally {
    paying.value = false
  }
}

function back() {
  router.push(`/listing/${route.params.id}`)
}

onMounted(loadListing)
</script>

<template>
  <div class="container booking-page">
    <div class="booking-head">
      <h1>确认订单</h1>
      <p class="head-sub">请核对住宿信息，支付后等待房东确认</p>
    </div>

    <div v-if="listing" class="booking-grid">
      <!-- 左：房源摘要 + 入住信息 -->
      <div class="left-col">
        <div class="card">
          <h3>住宿信息</h3>
          <div class="stay-row">
            <div class="stay-item">
              <label>入住</label>
              <span>{{ ci || '未选择' }}</span>
            </div>
            <div class="stay-arrow">→</div>
            <div class="stay-item">
              <label>退房</label>
              <span>{{ co || '未选择' }}</span>
            </div>
            <div class="stay-item">
              <label>人数</label>
              <span>{{ guests }} 位</span>
            </div>
            <div class="stay-item">
              <label>晚数</label>
              <span>{{ nights }} 晚</span>
            </div>
          </div>
        </div>

        <div class="card listing-summary">
          <img :src="listing.images?.[0] || '/img/listing0-0.svg'" :alt="listing.title" class="thumb"
            @error="$event.target.style.display = 'none'" />
          <div>
            <h4>{{ listing.title }}</h4>
            <p class="loc">{{ listing.city }} · {{ listing.district }} · {{ listing.address }}</p>
            <p class="tip">押金 ¥{{ listing.deposit_amount }} · 退房查房无损原路退还</p>
          </div>
        </div>
      </div>

      <!-- 右：金额明细 + 操作 -->
      <div class="right-col">
        <div class="card price-card">
          <h3>金额明细</h3>
          <template v-if="detail">
            <div v-for="n in detail.nightly" :key="n.date" class="price-line">
              <span>{{ n.date }}</span>
              <span>¥{{ n.price }}</span>
            </div>
            <div class="price-line">
              <span>房费小计</span>
              <span>¥{{ detail.subtotal }}</span>
            </div>
            <div v-if="detail.discount" class="price-line discount">
              <span>连住折扣</span>
              <span>-¥{{ detail.discount }}</span>
            </div>
            <div class="price-line">
              <span>清洁费</span>
              <span>¥{{ detail.cleaning_fee }}</span>
            </div>
            <div class="price-line total">
              <span>订单总额</span>
              <span>¥{{ total }}</span>
            </div>
          </template>
          <template v-else>
            <div class="price-line">
              <span>房费小计</span>
              <span>创建订单后按日历价格精确计算</span>
            </div>
            <div class="price-line total">
              <span>订单总额</span>
              <span>创建后显示</span>
            </div>
          </template>

          <!-- 未创建：提交订单；已创建待支付：去支付 -->
          <el-button v-if="!createdOrder" class="action" type="primary" size="large" round
            :loading="submitting" @click="submitOrder">
            提交订单
          </el-button>
          <el-button v-else-if="createdOrder.status === 'pending_pay'" class="action"
            type="primary" size="large" round :loading="paying" @click="pay">
            模拟支付 ¥{{ total }}
          </el-button>
          <el-button v-else class="action" type="primary" size="large" round disabled>
            已支付，等待确认
          </el-button>
          <el-button class="back" text @click="back">返回修改</el-button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.booking-page {
  padding: 32px 0 64px;
}

.booking-head h1 {
  font-size: 26px;
  font-weight: 800;
}
.head-sub {
  color: var(--ink-2);
  font-size: 14px;
  margin: 6px 0 24px;
}

.booking-grid {
  display: grid;
  grid-template-columns: 1fr 400px;
  gap: 24px;
  align-items: start;
}

.card {
  background: #fff;
  border-radius: var(--radius);
  box-shadow: var(--shadow);
  padding: 20px;
  margin-bottom: 16px;
}
.card h3 {
  font-size: 16px;
  margin-bottom: 14px;
}

.stay-row {
  display: flex;
  align-items: center;
  gap: 20px;
  flex-wrap: wrap;
}
.stay-item {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.stay-item label {
  font-size: 11px;
  color: var(--ink-2);
  font-weight: 600;
}
.stay-item span {
  font-size: 15px;
  font-weight: 600;
}
.stay-arrow {
  color: var(--ink-2);
  margin-top: 14px;
}

.listing-summary {
  display: flex;
  gap: 14px;
}
.thumb {
  width: 120px;
  height: 90px;
  border-radius: 12px;
  object-fit: cover;
  flex-shrink: 0;
}
.listing-summary h4 {
  font-size: 15px;
}
.loc {
  font-size: 13px;
  color: var(--ink-2);
  margin: 4px 0;
}
.tip {
  font-size: 12px;
  color: var(--ink-2);
}

.price-card {
  position: sticky;
  top: 88px;
}
.price-line {
  display: flex;
  justify-content: space-between;
  font-size: 14px;
  color: var(--ink-2);
  padding: 6px 0;
}
.price-line.discount {
  color: #16a34a;
}
.price-line.total {
  border-top: 1px solid var(--line);
  margin-top: 8px;
  padding-top: 12px;
  color: var(--ink);
  font-weight: 700;
  font-size: 16px;
}

.action {
  width: 100%;
  margin-top: 16px;
  font-weight: 700;
}
.back {
  width: 100%;
  margin-top: 8px;
}

@media (max-width: 900px) {
  .booking-grid {
    grid-template-columns: 1fr;
  }
  .price-card {
    position: static;
  }
}
</style>
