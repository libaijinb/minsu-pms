<script setup>
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { assignCleaningTask, finishCleaningTask, listCleaningTasks, reviewCleaningTask } from '../../api/services'
import { listUsers } from '../../api/auth'
import { useUserStore } from '../../stores/user'

/**
 * 清洁任务：
 * - 运营：派工（冲突检测 409 提示）、复核关单
 * - 保洁：查看派给自己的任务、提交完成（照片）
 * - 房东：查看自己房源的任务
 */
const userStore = useUserStore()

const list = ref([])
const loading = ref(false)
const filterStatus = ref('')
const cleaners = ref([])

const statusMap = {
  pending: { label: '待派工', type: 'warning' },
  assigned: { label: '已派工', type: 'primary' },
  doing: { label: '进行中', type: 'primary' },
  reviewing: { label: '待复核', type: 'warning' },
  done: { label: '已完成', type: 'success' },
}

// 派工弹窗
const dispatchDialog = ref(false)
const dispatchForm = ref({ id: null, cleaner: null, task_date: '', slot: 'morning' })
// 完成弹窗
const finishDialog = ref(false)
const finishForm = ref({ id: null, photos: '' })

async function loadData() {
  loading.value = true
  try {
    const params = { page_size: 100 }
    if (filterStatus.value) params.status = filterStatus.value
    const data = await listCleaningTasks(params)
    list.value = data.results || []
  } finally {
    loading.value = false
  }
}

async function loadCleaners() {
  const data = await listUsers({ role: 'cleaner', page_size: 50 })
  cleaners.value = data.results || []
}

// 运营视角看全部；保洁只看自己的
const visibleList = computed(() => {
  if (userStore.isOperator || userStore.isLandlord) return list.value
  return list.value.filter((t) => t.cleaner === userStore.userInfo?.id)
})

function openDispatch(row) {
  dispatchForm.value = { id: row.id, cleaner: null, task_date: row.task_date, slot: row.slot }
  dispatchDialog.value = true
}

async function doDispatch() {
  if (!dispatchForm.value.cleaner) {
    ElMessage.warning('请选择保洁')
    return
  }
  try {
    await assignCleaningTask(dispatchForm.value.id, {
      cleaner: dispatchForm.value.cleaner,
      task_date: dispatchForm.value.task_date,
      slot: dispatchForm.value.slot,
    })
    ElMessage.success('派工成功')
    dispatchDialog.value = false
    loadData()
  } catch {
    // 409 冲突提示由拦截器弹出："该保洁在此日期时段已有任务"
  }
}

function openFinish(row) {
  finishForm.value = { id: row.id, photos: '' }
  finishDialog.value = true
}

async function doFinish() {
  const photos = finishForm.value.photos.split('\n').map((s) => s.trim()).filter(Boolean)
  if (!photos.length) {
    ElMessage.warning('请至少填写 1 张照片链接')
    return
  }
  await finishCleaningTask(finishForm.value.id, photos)
  ElMessage.success('已提交完成，等待运营复核')
  finishDialog.value = false
  loadData()
}

async function review(row) {
  await reviewCleaningTask(row.id)
  ElMessage.success('复核通过，任务完成')
  loadData()
}

onMounted(async () => {
  if (userStore.isOperator) await loadCleaners()
  await loadData()
})
</script>

<template>
  <div class="page">
    <div class="toolbar">
      <h2 class="page-title">清洁任务</h2>
      <el-select v-model="filterStatus" placeholder="状态筛选" clearable style="width: 140px" @change="loadData">
        <el-option v-for="(v, k) in statusMap" :key="k" :label="v.label" :value="k" />
      </el-select>
    </div>

    <el-table v-loading="loading" :data="visibleList" stripe>
      <el-table-column prop="task_date" label="日期" width="130">
        <template #default="{ row }">{{ row.task_date }} {{ row.slot_display }}</template>
      </el-table-column>
      <el-table-column prop="listing_title" label="房源" min-width="160" show-overflow-tooltip />
      <el-table-column prop="listing_address" label="地址" min-width="160" show-overflow-tooltip />
      <el-table-column prop="cleaner_name" label="保洁" width="90">
        <template #default="{ row }">{{ row.cleaner_name || '未派工' }}</template>
      </el-table-column>
      <el-table-column label="状态" width="100">
        <template #default="{ row }">
          <el-tag :type="statusMap[row.status]?.type" size="small">{{ statusMap[row.status]?.label }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="照片" width="80">
        <template #default="{ row }">{{ row.photos?.length || 0 }} 张</template>
      </el-table-column>
      <el-table-column label="操作" width="200" fixed="right">
        <template #default="{ row }">
          <template v-if="row.status === 'pending'">
            <el-button v-if="userStore.isOperator" text type="primary" @click="openDispatch(row)">派工</el-button>
            <span v-else class="muted">等待派工</span>
          </template>
          <template v-else-if="row.status === 'assigned'">
            <el-button v-if="row.cleaner === userStore.userInfo?.id || userStore.isOperator" text
              type="primary" @click="openFinish(row)">提交完成</el-button>
            <el-button v-if="userStore.isOperator" text type="primary" @click="openDispatch(row)">改派</el-button>
          </template>
          <template v-else-if="row.status === 'reviewing'">
            <el-button v-if="userStore.isOperator" text type="success" @click="review(row)">复核通过</el-button>
            <span v-else class="muted">待复核</span>
          </template>
          <span v-else class="muted">—</span>
        </template>
      </el-table-column>
      <template #empty><span class="empty-tip">暂无清洁任务</span></template>
    </el-table>

    <!-- 派工弹窗 -->
    <el-dialog v-model="dispatchDialog" title="派工" width="420px">
      <el-form label-position="top">
        <el-form-item label="保洁员" required>
          <el-select v-model="dispatchForm.cleaner" placeholder="选择保洁" style="width: 100%">
            <el-option v-for="c in cleaners" :key="c.id" :label="`${c.first_name || c.username}（${c.phone || '无电话'}）`" :value="c.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="任务日期">
          <el-date-picker v-model="dispatchForm.task_date" type="date" value-format="YYYY-MM-DD" style="width: 100%" />
        </el-form-item>
        <el-form-item label="时段">
          <el-radio-group v-model="dispatchForm.slot">
            <el-radio-button value="morning">上午</el-radio-button>
            <el-radio-button value="afternoon">下午</el-radio-button>
          </el-radio-group>
        </el-form-item>
        <p class="conflict-tip">提示：同一保洁同一日期同一时段只能有一个任务，冲突时后端会拒绝</p>
      </el-form>
      <template #footer>
        <el-button @click="dispatchDialog = false">取消</el-button>
        <el-button type="primary" @click="doDispatch">确认派工</el-button>
      </template>
    </el-dialog>

    <!-- 完成弹窗 -->
    <el-dialog v-model="finishDialog" title="提交完成" width="460px">
      <el-form label-position="top">
        <el-form-item label="完成照片链接（每行一条）" required>
          <el-input v-model="finishForm.photos" type="textarea" :rows="4"
            placeholder="https://picsum.photos/seed/clean1/800/600&#10;https://picsum.photos/seed/clean2/800/600" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="finishDialog = false">取消</el-button>
        <el-button type="primary" @click="doFinish">提交</el-button>
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
.conflict-tip {
  font-size: 12px;
  color: var(--ink-2);
  background: #fef3c7;
  border-radius: 8px;
  padding: 8px 12px;
}
</style>
