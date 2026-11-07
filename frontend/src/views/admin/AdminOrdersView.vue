<script setup>
import { onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { cancelOrder, checkinOrder, checkoutOrder, confirmOrder, listOrders, noshowOrder } from '../../api/orders'
import { useUserStore } from '../../stores/user'

/**
 * 订单管理（运营/房东）：状态机动作面板。
 * 房东只能确认/取消自己房源的订单；入住退房 no-show 是运营动作。
 */
const route = useRoute()
const userStore = useUserStore()

const list = ref([])
const loading = ref(false)
const filterStatus = ref(route.query.status || '')

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

// 入住登记弹窗
const checkinDialog = ref(false)
const checkinForm = ref({ order_no: '', guest_names: [], id_card: '', phone: '', deposit_amount: 500 })

async function loadData() {
  loading.value = true
  try {
    const params = { page_size: 50 }
    if (filterStatus.value) params.status = filterStatus.value
    const data = await listOrders(params)
    list.value = data.results || []
  } finally {
    loading.value = false
  }
}

async function confirm(row) {
  await ElMessageBox.confirm(`确认订单 ${row.order_no}？`, '确认订单')
  await confirmOrder(row.order_no)
  ElMessage.success('已确认')
  loadData()
}

async function cancel(row) {
  const { value } = await ElMessageBox.prompt('取消原因（客人可见）', '取消订单', {
    confirmButtonText: '取消订单', cancelButtonText: '再想想', inputPlaceholder: '如：房屋临时维修',
  })
  const res = await cancelOrder(row.order_no, value)
  ElMessage.success(res.detail)
  loadData()
}

function openCheckin(row) {
  checkinForm.value = { order_no: row.order_no, guest_names: [], id_card: '', phone: '', deposit_amount: 500 }
  checkinDialog.value = true
}

async function doCheckin() {
  const payload = {
    guest_names: checkinForm.value.guest_names,
    id_card: checkinForm.value.id_card,
    phone: checkinForm.value.phone,
    deposit_amount: checkinForm.value.deposit_amount,
  }
  await checkinOrder(checkinForm.value.order_no, payload)
  ElMessage.success('入住登记完成，押金已记录')
  checkinDialog.value = false
  loadData()
}

async function checkout(row) {
  await ElMessageBox.confirm(`为订单 ${row.order_no} 办理退房？系统将自动生成清洁任务`, '办理退房')
  await checkoutOrder(row.order_no)
  ElMessage.success('已退房，清洁任务已自动生成')
  loadData()
}

async function noshow(row) {
  await ElMessageBox.confirm(`标记 ${row.order_no} 客人未入住？房费将全额扣除`, '标记未入住', { type: 'warning' })
  await noshowOrder(row.order_no)
  ElMessage.success('已标记未入住')
  loadData()
}

onMounted(loadData)
</script>

<template>
  <div class="page">
    <div class="toolbar">
      <h2 class="page-title">订单管理</h2>
      <el-select v-model="filterStatus" placeholder="状态筛选" clearable style="width: 160px" @change="loadData">
        <el-option v-for="(v, k) in statusMap" :key="k" :label="v.label" :value="k" />
      </el-select>
    </div>

    <el-table v-loading="loading" :data="list" stripe>
      <el-table-column prop="order_no" label="订单号" width="170" />
      <el-table-column prop="listing_title" label="房源" min-width="160" show-overflow-tooltip />
      <el-table-column prop="guest_name" label="客人" width="90" />
      <el-table-column label="入住/退房" width="200">
        <template #default="{ row }">
          {{ row.checkin_date }} → {{ row.checkout_date }}
          <span class="muted">（{{ row.nights }} 晚）</span>
        </template>
      </el-table-column>
      <el-table-column label="渠道" width="80">
        <template #default="{ row }">{{ row.channel_display }}</template>
      </el-table-column>
      <el-table-column prop="total_amount" label="金额" width="90">
        <template #default="{ row }">¥{{ row.total_amount }}</template>
      </el-table-column>
      <el-table-column label="状态" width="90">
        <template #default="{ row }">
          <el-tag :type="statusMap[row.status]?.type" size="small">{{ statusMap[row.status]?.label }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="240" fixed="right">
        <template #default="{ row }">
          <template v-if="row.status === 'pending_confirm'">
            <el-button text type="primary" @click="confirm(row)">确认</el-button>
            <el-button text type="danger" @click="cancel(row)">取消</el-button>
          </template>
          <template v-else-if="row.status === 'pending_pay'">
            <el-button text type="danger" @click="cancel(row)">取消</el-button>
          </template>
          <template v-else-if="row.status === 'confirmed'">
            <el-button v-if="userStore.isOperator" text type="primary" @click="openCheckin(row)">办理入住</el-button>
            <el-button text type="danger" @click="cancel(row)">取消</el-button>
          </template>
          <template v-else-if="row.status === 'checked_in'">
            <el-button v-if="userStore.isOperator" text type="primary" @click="checkout(row)">办理退房</el-button>
            <el-button v-if="userStore.isOperator" text type="warning" @click="noshow(row)">未入住</el-button>
          </template>
          <span v-else class="muted">—</span>
        </template>
      </el-table-column>
      <template #empty><span class="empty-tip">暂无订单</span></template>
    </el-table>

    <!-- 入住登记弹窗 -->
    <el-dialog v-model="checkinDialog" title="办理入住登记" width="480px">
      <el-form :model="checkinForm" label-position="top">
        <el-form-item label="入住人姓名（多位同住人逐行填写）">
          <el-input v-model="checkinForm.guest_names" type="textarea" :rows="2"
            placeholder="每行一位，如：张三&#10;李四" />
        </el-form-item>
        <el-form-item label="身份证号" required>
          <el-input v-model="checkinForm.id_card" maxlength="18" placeholder="18 位身份证号" />
        </el-form-item>
        <el-form-item label="联系电话" required>
          <el-input v-model="checkinForm.phone" maxlength="11" placeholder="11 位手机号" />
        </el-form-item>
        <el-form-item label="收取押金(元)">
          <el-input-number v-model="checkinForm.deposit_amount" :min="0" :step="100" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="checkinDialog = false">取消</el-button>
        <el-button type="primary" @click="doCheckin">登记入住</el-button>
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
.muted {
  color: #9ca3af;
  font-size: 12px;
}
.empty-tip {
  color: var(--ink-2);
  font-size: 13px;
}
</style>
