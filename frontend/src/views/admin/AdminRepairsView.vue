<script setup>
import { computed, onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  assignRepairTicket, closeRepairTicket, createRepairTicket,
  handleRepairTicket, listRepairTickets,
} from '../../api/services'
import { listListings } from '../../api/listings'
import { listUsers } from '../../api/auth'
import { useUserStore } from '../../stores/user'

/**
 * 维修工单：
 * - 报修入口（客人/房东/运营）：房源 + 问题描述 + 紧急程度
 * - 运营：派工、验收关单；紧急工单派工时自动锁定房源日期
 * - 维修师傅：查看派给自己的工单、提交处理结果（费用）
 */
const userStore = useUserStore()

const list = ref([])
const loading = ref(false)
const filterStatus = ref('')
const repairers = ref([])
const listings = ref([])

const statusMap = {
  pending: { label: '待派工', type: 'warning' },
  assigned: { label: '已派工', type: 'primary' },
  doing: { label: '处理中', type: 'primary' },
  accepting: { label: '待验收', type: 'warning' },
  done: { label: '已完成', type: 'success' },
  closed: { label: '已关闭', type: 'info' },
}
const urgencyMap = { normal: { label: '一般', type: 'info' }, urgent: { label: '紧急', type: 'danger' } }

// 报修弹窗
const reportDialog = ref(false)
const reportForm = ref({ listing: null, title: '', desc: '', urgency: 'normal' })
// 派工弹窗
const dispatchDialog = ref(false)
const dispatchForm = ref({ id: null, repairer: null })
// 处理弹窗
const handleDialog = ref(false)
const handleForm = ref({ id: null, cost: 0, note: '' })

async function loadData() {
  loading.value = true
  try {
    const params = { page_size: 100 }
    if (filterStatus.value) params.status = filterStatus.value
    const data = await listRepairTickets(params)
    list.value = data.results || []
  } finally {
    loading.value = false
  }
}

async function loadOptions() {
  const [repairerData, listingData] = await Promise.all([
    listUsers({ role: 'repairer', page_size: 50 }),
    listListings({ page_size: 50 }),
  ])
  repairers.value = repairerData.results || []
  listings.value = listingData.results || []
}

// 运营/房东看全部；维修师傅看自己的；客人看自己报修的
const visibleList = computed(() => {
  if (userStore.isOperator || userStore.isLandlord) return list.value
  if (userStore.isRepairer) return list.value.filter((t) => t.repairer === userStore.userInfo?.id)
  return list.value
})

function openReport() {
  reportForm.value = { listing: listings.value[0]?.id || null, title: '', desc: '', urgency: 'normal' }
  reportDialog.value = true
}

async function doReport() {
  if (!reportForm.value.listing || !reportForm.value.title) {
    ElMessage.warning('请选择房源并填写标题')
    return
  }
  await createRepairTicket(reportForm.value)
  ElMessage.success('报修已提交')
  reportDialog.value = false
  loadData()
}

function openDispatch(row) {
  dispatchForm.value = { id: row.id, repairer: null }
  dispatchDialog.value = true
}

async function doDispatch() {
  if (!dispatchForm.value.repairer) {
    ElMessage.warning('请选择维修师傅')
    return
  }
  await assignRepairTicket(dispatchForm.value.id, dispatchForm.value.repairer)
  ElMessage.success('派工成功')
  dispatchDialog.value = false
  loadData()
}

function openHandle(row) {
  handleForm.value = { id: row.id, cost: 0, note: '' }
  handleDialog.value = true
}

async function doHandle() {
  await handleRepairTicket(handleForm.value.id, { cost: handleForm.value.cost, note: handleForm.value.note })
  ElMessage.success('处理结果已提交，等待验收')
  handleDialog.value = false
  loadData()
}

async function close(row) {
  await ElMessageBox.confirm(`验收工单「${row.title}」并关单？`, '验收关单', { type: 'warning' })
  await closeRepairTicket(row.id)
  ElMessage.success('工单已完成')
  loadData()
}

onMounted(async () => {
  await Promise.all([loadData(), loadOptions()])
})
</script>

<template>
  <div class="page">
    <div class="toolbar">
      <h2 class="page-title">维修工单</h2>
      <div class="ops">
        <el-select v-model="filterStatus" placeholder="状态筛选" clearable style="width: 140px" @change="loadData">
          <el-option v-for="(v, k) in statusMap" :key="k" :label="v.label" :value="k" />
        </el-select>
        <el-button type="primary" round @click="openReport">+ 报修</el-button>
      </div>
    </div>

    <el-table v-loading="loading" :data="visibleList" stripe>
      <el-table-column prop="title" label="标题" min-width="160" show-overflow-tooltip />
      <el-table-column prop="listing_title" label="房源" min-width="140" show-overflow-tooltip />
      <el-table-column label="紧急度" width="90">
        <template #default="{ row }">
          <el-tag :type="urgencyMap[row.urgency]?.type" size="small" effect="light">
            {{ urgencyMap[row.urgency]?.label }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="来源" width="100">
        <template #default="{ row }">{{ row.source_display }}</template>
      </el-table-column>
      <el-table-column prop="repairer_name" label="维修" width="90">
        <template #default="{ row }">{{ row.repairer_name || '未派工' }}</template>
      </el-table-column>
      <el-table-column prop="cost" label="费用" width="80">
        <template #default="{ row }">{{ row.cost ? `¥${row.cost}` : '-' }}</template>
      </el-table-column>
      <el-table-column label="状态" width="100">
        <template #default="{ row }">
          <el-tag :type="statusMap[row.status]?.type" size="small">{{ statusMap[row.status]?.label }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="220" fixed="right">
        <template #default="{ row }">
          <template v-if="row.status === 'pending'">
            <el-button v-if="userStore.isOperator" text type="primary" @click="openDispatch(row)">派工</el-button>
            <span v-else class="muted">等待派工</span>
          </template>
          <template v-else-if="row.status === 'assigned'">
            <el-button v-if="row.repairer === userStore.userInfo?.id" text type="primary" @click="openHandle(row)">提交处理</el-button>
            <el-button v-if="userStore.isOperator" text type="primary" @click="openDispatch(row)">改派</el-button>
          </template>
          <template v-else-if="row.status === 'accepting'">
            <el-button v-if="userStore.isOperator" text type="success" @click="close(row)">验收关单</el-button>
            <span v-else class="muted">待验收</span>
          </template>
          <span v-else class="muted">—</span>
        </template>
      </el-table-column>
      <template #empty><span class="empty-tip">暂无维修工单</span></template>
    </el-table>

    <!-- 报修弹窗 -->
    <el-dialog v-model="reportDialog" title="提交报修" width="480px">
      <el-form :model="reportForm" label-position="top">
        <el-form-item label="房源" required>
          <el-select v-model="reportForm.listing" style="width: 100%">
            <el-option v-for="l in listings" :key="l.id" :label="l.title" :value="l.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="问题标题" required>
          <el-input v-model="reportForm.title" maxlength="100" placeholder="如：热水器不出热水" />
        </el-form-item>
        <el-form-item label="详细描述">
          <el-input v-model="reportForm.desc" type="textarea" :rows="3" placeholder="具体情况、发生时间" />
        </el-form-item>
        <el-form-item label="紧急程度">
          <el-radio-group v-model="reportForm.urgency">
            <el-radio-button value="normal">一般</el-radio-button>
            <el-radio-button value="urgent">紧急（影响入住）</el-radio-button>
          </el-radio-group>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="reportDialog = false">取消</el-button>
        <el-button type="primary" @click="doReport">提交报修</el-button>
      </template>
    </el-dialog>

    <!-- 派工弹窗 -->
    <el-dialog v-model="dispatchDialog" title="派工给维修师傅" width="420px">
      <el-form label-position="top">
        <el-form-item label="维修师傅" required>
          <el-select v-model="dispatchForm.repairer" placeholder="选择维修" style="width: 100%">
            <el-option v-for="r in repairers" :key="r.id" :label="`${r.first_name || r.username}（${r.phone || '无电话'}）`" :value="r.id" />
          </el-select>
        </el-form-item>
      </el-form>
      <p class="tip">紧急工单派工后将自动锁定房源当天与次日的日历（BR-REP-03）</p>
      <template #footer>
        <el-button @click="dispatchDialog = false">取消</el-button>
        <el-button type="primary" @click="doDispatch">确认派工</el-button>
      </template>
    </el-dialog>

    <!-- 处理弹窗 -->
    <el-dialog v-model="handleDialog" title="提交处理结果" width="440px">
      <el-form label-position="top">
        <el-form-item label="维修费用(元)">
          <el-input-number v-model="handleForm.cost" :min="0" :step="10" style="width: 100%" />
        </el-form-item>
        <el-form-item label="处理说明">
          <el-input v-model="handleForm.note" type="textarea" :rows="3" placeholder="更换了什么、是否已修复" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="handleDialog = false">取消</el-button>
        <el-button type="primary" @click="doHandle">提交</el-button>
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
.ops {
  display: flex;
  gap: 10px;
}
.muted {
  color: #9ca3af;
  font-size: 12px;
}
.empty-tip {
  color: var(--ink-2);
  font-size: 13px;
}
.tip {
  font-size: 12px;
  color: var(--ink-2);
  background: #fef3c7;
  border-radius: 8px;
  padding: 8px 12px;
}
</style>
