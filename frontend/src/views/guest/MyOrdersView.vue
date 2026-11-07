<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { cancelOrder, getOrder, listOrders, payOrder } from '../../api/orders'
import { createReview } from '../../api/core'

/**
 * 我的订单：状态 Tab + 订单卡列表。
 * 操作按状态机开放：待支付→支付/取消；待确认→取消；已退房→评价。
 * 详情弹窗展示金额快照明细 + 状态流水（后端全量返回）。
 */
const router = useRouter()
const orders = ref([])
const loading = ref(false)
const activeTab = ref('')
const detail = ref(null)
const detailVisible = ref(false)
const reviewDialog = ref(false)
const reviewForm = ref({ order_no: '', rating: 5, content: '' })

const statusMap = {
  pending_pay: { label: '待支付', type: 'warning' },
  pending_confirm: { label: '待确认', type: 'warning' },
  confirmed: { label: '已确认', type: 'primary' },
  checked_in: { label: '入住中', type: 'success' },
  checked_out: { label: '已退房', type: 'info' },
  disputed: { label: '争议中', type: 'danger' },
  cancelled: { label: '已取消', type: 'info' },
  settled: { label: '已结算', type: 'success' },
}

const tabs = [
  { label: '全部', value: '' },
  { label: '待支付', value: 'pending_pay' },
  { label: '待确认', value: 'pending_confirm' },
  { label: '已确认', value: 'confirmed' },
  { label: '入住中', value: 'checked_in' },
  { label: '已退房', value: 'checked_out' },
  { label: '已取消', value: 'cancelled' },
]

const filtered = computed(() =>
  activeTab.value ? orders.value.filter((o) => o.status === activeTab.value) : orders.value)

async function loadOrders() {
  loading.value = true
  try {
    const data = await listOrders({ page_size: 50 })
    orders.value = data.results || []
  } finally {
    loading.value = false
  }
}

async function pay(order) {
  await payOrder(order.order_no)
  ElMessage.success('支付成功')
  loadOrders()
}

async function cancel(order) {
  await ElMessageBox.confirm(`确定取消订单 ${order.order_no}？退款按取消政策计算`, '取消订单', {
    type: 'warning', confirmButtonText: '取消订单', cancelButtonText: '再想想',
  })
  const res = await cancelOrder(order.order_no, '客人主动取消')
  ElMessage.success(res.detail || '已取消')
  loadOrders()
}

async function showDetail(order) {
  detail.value = await getOrder(order.order_no)
  detailVisible.value = true
}

function openReview(order) {
  reviewForm.value = { order_no: order.order_no, rating: 5, content: '' }
  reviewDialog.value = true
}

async function submitReview() {
  await createReview({ ...reviewForm.value, type: 'guest_to_listing' })
  ElMessage.success('评价成功，感谢分享')
  reviewDialog.value = false
  loadOrders()
}

onMounted(loadOrders)
</script>

<template>
  <div class="container my-orders">
    <h1 class="page-title">我的订单</h1>

    <el-tabs v-model="activeTab" class="tabs" @tab-change="() => {}">
      <el-tab-pane v-for="t in tabs" :key="t.value" :label="t.label" :name="t.value" />
    </el-tabs>

    <div v-loading="loading" class="order-list">
      <div v-for="o in filtered" :key="o.order_no" class="order-card">
        <img class="thumb" :src="o.listing_image || '/img/listing0-0.svg'" :alt="o.listing_title"
          @error="$event.target.style.display = 'none'" />
        <div class="order-main">
          <div class="order-row">
            <span class="order-title">{{ o.listing_title }}</span>
            <el-tag :type="statusMap[o.status]?.type" size="small">
              {{ statusMap[o.status]?.label || o.status }}
            </el-tag>
          </div>
          <p class="order-meta">
            {{ o.checkin_date }} 至 {{ o.checkout_date }} · {{ o.nights }} 晚 · {{ o.guests_count }} 人
          </p>
          <p class="order-no">订单号 {{ o.order_no }}</p>
        </div>
        <div class="order-side">
          <span class="amount">¥{{ o.total_amount }}</span>
          <div class="ops">
            <el-button text type="primary" @click="showDetail(o)">详情</el-button>
            <el-button v-if="o.status === 'pending_pay'" text type="primary" @click="pay(o)">支付</el-button>
            <el-button v-if="o.status === 'pending_pay' || o.status === 'pending_confirm'" text
              type="danger" @click="cancel(o)">取消</el-button>
            <el-button v-if="o.status === 'checked_out' || o.status === 'settled'" text
              type="primary" @click="openReview(o)">评价</el-button>
          </div>
        </div>
      </div>

      <el-empty v-if="!loading && filtered.length === 0" description="还没有相关订单，去发现页看看吧">
        <el-button type="primary" round @click="router.push('/')">去发现房源</el-button>
      </el-empty>
    </div>

    <!-- 订单详情：金额快照 + 状态流水 + 查房结果 -->
    <el-dialog v-model="detailVisible" title="订单详情" width="560px">
      <template v-if="detail">
        <el-descriptions :column="2" border size="small">
          <el-descriptions-item label="订单号">{{ detail.order_no }}</el-descriptions-item>
          <el-descriptions-item label="状态">{{ statusMap[detail.status]?.label }}</el-descriptions-item>
          <el-descriptions-item label="入住">{{ detail.checkin_date }}</el-descriptions-item>
          <el-descriptions-item label="退房">{{ detail.checkout_date }}</el-descriptions-item>
          <el-descriptions-item label="房费小计">¥{{ detail.amount_detail?.subtotal }}</el-descriptions-item>
          <el-descriptions-item label="清洁费">¥{{ detail.amount_detail?.cleaning_fee }}</el-descriptions-item>
          <el-descriptions-item label="连住折扣">-¥{{ detail.amount_detail?.discount || 0 }}</el-descriptions-item>
          <el-descriptions-item label="订单总额">¥{{ detail.total_amount }}</el-descriptions-item>
          <el-descriptions-item v-if="detail.refund_amount" label="已退金额">¥{{ detail.refund_amount }}</el-descriptions-item>
          <el-descriptions-item v-if="detail.cancel_reason" label="取消原因">{{ detail.cancel_reason }}</el-descriptions-item>
        </el-descriptions>

        <h4 class="section-title">入住登记</h4>
        <p v-if="detail.checkin" class="detail-line">
          入住人：{{ detail.checkin.guest_names?.join('、') }} · 押金 ¥{{ detail.checkin.deposit_amount }}
          （{{ detail.checkin.deposit_status_display }}）
        </p>
        <p v-else class="detail-line muted">尚未办理入住</p>

        <h4 class="section-title">查房结果</h4>
        <p v-if="detail.inspection" class="detail-line">
          结论：{{ detail.inspection.conclusion_display }} · 定损 ¥{{ detail.inspection.damage_total }}
        </p>
        <p v-else class="detail-line muted">暂无查房记录</p>

        <h4 class="section-title">状态流水</h4>
        <el-timeline class="timeline">
          <el-timeline-item v-for="log in detail.logs" :key="log.id" size="small"
            :timestamp="log.created_at" placement="top">
            {{ log.from_status || '创建' }} → {{ log.to_status }}（{{ log.operator_name }}）
            <span v-if="log.remark" class="muted"> · {{ log.remark }}</span>
          </el-timeline-item>
        </el-timeline>
      </template>
    </el-dialog>

    <!-- 评价弹窗 -->
    <el-dialog v-model="reviewDialog" title="发表评价" width="440px">
      <el-form label-position="top">
        <el-form-item label="评分">
          <el-rate v-model="reviewForm.rating" />
        </el-form-item>
        <el-form-item label="评价内容">
          <el-input v-model="reviewForm.content" type="textarea" :rows="4"
            placeholder="说说这次住宿的感受吧" maxlength="1000" show-word-limit />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="reviewDialog = false">取消</el-button>
        <el-button type="primary" @click="submitReview">提交评价</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.my-orders {
  padding: 32px 0 64px;
}

.page-title {
  font-size: 26px;
  font-weight: 800;
  margin-bottom: 8px;
}

.tabs {
  margin-bottom: 8px;
}
.tabs :deep(.el-tabs__item) {
  font-size: 14px;
}

.order-list {
  display: flex;
  flex-direction: column;
  gap: 14px;
  min-height: 200px;
}

.order-card {
  display: flex;
  gap: 16px;
  background: #fff;
  border-radius: var(--radius);
  box-shadow: var(--shadow);
  padding: 14px;
  align-items: center;
}
.thumb {
  width: 120px;
  height: 90px;
  border-radius: 12px;
  object-fit: cover;
  flex-shrink: 0;
}

.order-main {
  flex: 1;
  min-width: 0;
}
.order-row {
  display: flex;
  align-items: center;
  gap: 10px;
}
.order-title {
  font-weight: 700;
  font-size: 15px;
}
.order-meta {
  font-size: 13px;
  color: var(--ink-2);
  margin-top: 6px;
}
.order-no {
  font-size: 12px;
  color: #9ca3af;
  margin-top: 2px;
}

.order-side {
  text-align: right;
  flex-shrink: 0;
}
.amount {
  display: block;
  font-size: 18px;
  font-weight: 800;
  color: var(--brand);
  margin-bottom: 6px;
}
.ops {
  display: flex;
  gap: 4px;
  justify-content: flex-end;
}

.section-title {
  font-size: 15px;
  margin: 18px 0 8px;
}
.detail-line {
  font-size: 14px;
  color: var(--ink-2);
}
.muted {
  color: #9ca3af;
}

.timeline {
  padding-left: 4px;
}

@media (max-width: 640px) {
  .order-card {
    flex-wrap: wrap;
  }
  .thumb {
    width: 100%;
    height: 160px;
  }
  .order-side {
    width: 100%;
    text-align: left;
  }
  .ops {
    justify-content: flex-start;
  }
}
</style>
