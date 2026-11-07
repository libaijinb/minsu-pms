<script setup>
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { listSettlements, payoutSettlement, retryPayout, runSettlement } from '../../api/finance'
import { listUsers } from '../../api/auth'
import { useUserStore } from '../../stores/user'

/**
 * 结算分账：
 * - 财务：执行分账、失败重试、手动触发月结（演示/补跑）
 * - 房东：查看自己的结算单与明细（只读）
 * - 公式：房东应得 = 订单实付 − 佣金(按渠道率) − 保洁成本 − 损坏赔付（BR-STL-01）
 */
const userStore = useUserStore()

const list = ref([])
const loading = ref(false)
const detailVisible = ref(false)
const detail = ref(null)
const landlords = ref([])
const runDialog = ref(false)
const runForm = ref({ landlord: null, period: '' })

const statusMap = {
  pending: { label: '待分账', type: 'warning' },
  paying: { label: '分账中', type: 'primary' },
  paid: { label: '已分账', type: 'success' },
  failed: { label: '分账失败', type: 'danger' },
}

async function loadData() {
  loading.value = true
  try {
    const data = await listSettlements({ page_size: 100 })
    list.value = data.results || []
  } finally {
    loading.value = false
  }
}

async function payout(row) {
  await payoutSettlement(row.id)
  ElMessage.success('分账完成')
  loadData()
}

// 演示分账失败：财务可模拟失败走重试流程（BR-STL-05）
async function payoutFail(row) {
  await payoutSettlement(row.id, false)
  ElMessage.warning('已模拟分账失败，可点击重试')
  loadData()
}

async function retry(id) {
  await retryPayout(id)
  ElMessage.success('重试成功')
  loadData()
}

async function showDetail(row) {
  const { getSettlement } = await import('../../api/finance')
  detail.value = await getSettlement(row.id)
  detailVisible.value = true
}

function openRun() {
  runForm.value = { landlord: landlords.value[0]?.id || null, period: '' }
  runDialog.value = true
}

async function doRun() {
  const res = await runSettlement({ landlord: runForm.value.landlord, period: runForm.value.period || undefined })
  ElMessage.success(res.detail || `结算单已生成：¥${res.net_amount}`)
  runDialog.value = false
  loadData()
}

onMounted(async () => {
  if (userStore.isOperator) {
    const data = await listUsers({ role: 'landlord', page_size: 50 })
    landlords.value = data.results || []
  }
  await loadData()
})
</script>

<template>
  <div class="page">
    <div class="toolbar">
      <h2 class="page-title">结算分账</h2>
      <el-button v-if="userStore.isOperator" round @click="openRun">手动月结</el-button>
    </div>

    <el-table v-loading="loading" :data="list" stripe>
      <el-table-column prop="period" label="周期" width="100" />
      <el-table-column prop="landlord_name" label="房东" width="100" />
      <el-table-column prop="order_count" label="订单数" width="80" />
      <el-table-column label="金额构成" min-width="300">
        <template #default="{ row }">
          <span class="calc">
            实付 ¥{{ row.gross }} − 佣金 ¥{{ row.commission }} − 保洁 ¥{{ row.service_cost }} − 赔付 ¥{{ row.damage }}
            = <b>¥{{ row.net_amount }}</b>
          </span>
        </template>
      </el-table-column>
      <el-table-column label="状态" width="100">
        <template #default="{ row }">
          <el-tag :type="statusMap[row.status]?.type" size="small">{{ statusMap[row.status]?.label }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="created_at" label="生成时间" width="170" />
      <el-table-column label="操作" width="240" fixed="right">
        <template #default="{ row }">
          <el-button text type="primary" @click="showDetail(row)">明细</el-button>
          <template v-if="userStore.isFinance || userStore.isOperator">
            <el-button v-if="row.status !== 'paid'" text type="success" @click="payout(row)">执行分账</el-button>
            <el-button v-if="row.status !== 'paid'" text type="warning" @click="payoutFail(row)">模拟失败</el-button>
          </template>
        </template>
      </el-table-column>
      <template #empty><span class="empty-tip">暂无结算单，每月 1 日系统自动月结</span></template>
    </el-table>

    <!-- 结算明细：订单级清单 + 分账记录 -->
    <el-dialog v-model="detailVisible" title="结算单明细" width="640px">
      <template v-if="detail">
        <el-descriptions :column="2" border size="small" class="detail-desc">
          <el-descriptions-item label="周期">{{ detail.period }}</el-descriptions-item>
          <el-descriptions-item label="房东">{{ detail.landlord_name }}</el-descriptions-item>
          <el-descriptions-item label="订单实付">¥{{ detail.gross }}</el-descriptions-item>
          <el-descriptions-item label="平台佣金">-¥{{ detail.commission }}</el-descriptions-item>
          <el-descriptions-item label="保洁成本">-¥{{ detail.service_cost }}</el-descriptions-item>
          <el-descriptions-item label="损坏赔付">-¥{{ detail.damage }}</el-descriptions-item>
          <el-descriptions-item label="房东应得">
            <b class="net">¥{{ detail.net_amount }}</b>
          </el-descriptions-item>
        </el-descriptions>

        <h4 class="section-title">包含订单（{{ detail.orders?.length }}）</h4>
        <el-table :data="detail.orders" size="small" empty-text="无订单">
          <el-table-column prop="order_no" label="订单号" width="180" />
          <el-table-column prop="listing_title" label="房源" min-width="140" show-overflow-tooltip />
          <el-table-column prop="checkout_date" label="退房日" width="120" />
          <el-table-column prop="channel" label="渠道" width="80" />
          <el-table-column prop="total_amount" label="实付" width="90">
            <template #default="{ row }">¥{{ row.total_amount }}</template>
          </el-table-column>
        </el-table>

        <h4 class="section-title">分账记录</h4>
        <el-table :data="detail.payouts" size="small" empty-text="暂无分账记录">
          <el-table-column prop="amount" label="金额" width="100">
            <template #default="{ row }">¥{{ row.amount }}</template>
          </el-table-column>
          <el-table-column label="状态" width="100">
            <template #default="{ row }">
              <el-tag :type="row.status === 'success' ? 'success' : row.status === 'failed' ? 'danger' : 'warning'" size="small">
                {{ row.status_display }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="trade_no" label="流水号" min-width="140" />
          <el-table-column prop="retry_count" label="重试次数" width="90" />
          <el-table-column label="操作" width="90">
            <template #default="{ row }">
              <el-button v-if="row.status === 'failed'" text type="primary" size="small"
                @click="retry(row.id); detailVisible = false">重试</el-button>
            </template>
          </el-table-column>
        </el-table>
      </template>
    </el-dialog>

    <!-- 手动月结弹窗（演示/补跑用） -->
    <el-dialog v-model="runDialog" title="手动触发月结" width="420px">
      <el-form label-position="top">
        <el-form-item label="房东">
          <el-select v-model="runForm.landlord" style="width: 100%">
            <el-option v-for="l in landlords" :key="l.id" :label="l.first_name || l.username" :value="l.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="周期（留空 = 上一个自然月）">
          <el-input v-model="runForm.period" placeholder="如 2026-09" maxlength="7" />
        </el-form-item>
      </el-form>
      <p class="tip">月结为幂等操作：同一房东同一周期重复执行不会产生重复结算单</p>
      <template #footer>
        <el-button @click="runDialog = false">取消</el-button>
        <el-button type="primary" @click="doRun">执行月结</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}
.page-title {
  font-size: 18px;
  font-weight: 700;
}

.calc {
  font-size: 13px;
  color: var(--ink-2);
}
.calc b {
  color: var(--brand);
  font-size: 15px;
}

.section-title {
  font-size: 15px;
  margin: 18px 0 10px;
}
.detail-desc {
  margin-bottom: 8px;
}
.net {
  color: var(--brand);
  font-size: 16px;
}

.tip {
  font-size: 12px;
  color: var(--ink-2);
  background: #fef3c7;
  border-radius: 8px;
  padding: 8px 12px;
}
.empty-tip {
  color: var(--ink-2);
  font-size: 13px;
}
</style>
