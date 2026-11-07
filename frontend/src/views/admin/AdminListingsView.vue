<script setup>
import { onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  auditListing, createListing, listListings, offlineListing,
  onlineListing, submitListing, updateListing,
} from '../../api/listings'
import { useUserStore } from '../../stores/user'

/**
 * 房源管理（房东/运营）：
 * - 房东看自己的房源，运营看全部
 * - 状态流转：草稿→提交审核→（运营）审核→上架/驳回；上架 ⇄ 下架
 * - 每行操作按状态动态开放
 */
const router = useRouter()
const userStore = useUserStore()

const list = ref([])
const loading = ref(false)
const total = ref(0)
const filterStatus = ref('')

const statusMap = {
  draft: { label: '草稿', type: 'info' },
  pending: { label: '审核中', type: 'warning' },
  online: { label: '已上架', type: 'success' },
  offline: { label: '已下架', type: 'info' },
}

const dialog = ref(false)
const saving = ref(false)
const editingId = ref(null)
const form = reactive({
  title: '', type: 'whole', area: 0, max_guests: 2, bed_count: 1,
  province: '', city: '', district: '', address: '', description: '',
  facilities: [], deposit_amount: 500,
})
const facilityInput = ref('')

async function loadData() {
  loading.value = true
  try {
    const params = { page_size: 50 }
    if (filterStatus.value) params.status = filterStatus.value
    const data = await listListings(params)
    list.value = data.results || []
    total.value = data.count
  } finally {
    loading.value = false
  }
}

function openCreate() {
  editingId.value = null
  Object.assign(form, { title: '', type: 'whole', area: 0, max_guests: 2, bed_count: 1,
    province: '', city: '', district: '', address: '', description: '',
    facilities: [], deposit_amount: 500 })
  dialog.value = true
}

function openEdit(row) {
  editingId.value = row.id
  Object.assign(form, { ...row })
  dialog.value = true
}

async function save() {
  saving.value = true
  try {
    const payload = { ...form, facilities: facilityInput.value
      ? facilityInput.value.split(/[,，]/).map((s) => s.trim()).filter(Boolean)
      : form.facilities }
    if (editingId.value) {
      await updateListing(editingId.value, payload)
      ElMessage.success('已保存')
    } else {
      await createListing(payload)
      ElMessage.success('房源已创建（草稿）')
    }
    dialog.value = false
    loadData()
  } finally {
    saving.value = false
  }
}

async function submit(row) {
  await ElMessageBox.confirm(`提交「${row.title}」进入审核？`, '提交审核')
  await submitListing(row.id)
  ElMessage.success('已提交审核')
  loadData()
}

async function audit(row, passed) {
  if (passed) {
    await auditListing(row.id, true)
    ElMessage.success('审核通过，房源已上架')
  } else {
    const { value } = await ElMessageBox.prompt('请输入驳回理由', '驳回审核', {
      confirmButtonText: '驳回', cancelButtonText: '取消', inputPlaceholder: '如图片不符合规范',
    })
    await auditListing(row.id, false, value)
    ElMessage.success('已驳回')
  }
  loadData()
}

async function toggleOnline(row) {
  if (row.status === 'online') {
    await ElMessageBox.confirm(`下架「${row.title}」？有未入住订单的房源不能下架`, '下架确认')
    await offlineListing(row.id)
    ElMessage.success('已下架')
  } else {
    await onlineListing(row.id)
    ElMessage.success('已上架')
  }
  loadData()
}

onMounted(loadData)
</script>

<template>
  <div class="page">
    <div class="toolbar">
      <h2 class="page-title">房源管理</h2>
      <div class="ops">
        <el-select v-model="filterStatus" placeholder="状态筛选" clearable style="width: 140px" @change="loadData">
          <el-option v-for="(v, k) in statusMap" :key="k" :label="v.label" :value="k" />
        </el-select>
        <el-button type="primary" round @click="openCreate">+ 新建房源</el-button>
      </div>
    </div>

    <el-table v-loading="loading" :data="list" stripe>
      <el-table-column label="房源" min-width="220">
        <template #default="{ row }">
          <div class="listing-cell">
            <img :src="row.images?.[0] || '/img/listing0-0.svg'" class="thumb"
              @error="$event.target.style.display = 'none'" />
            <div>
              <p class="t">{{ row.title }}</p>
              <p class="sub">{{ row.city }} · {{ row.district }}</p>
            </div>
          </div>
        </template>
      </el-table-column>
      <el-table-column label="类型" width="110">
        <template #default="{ row }">{{ { whole: '整套', room: '独立房间', share: '合租' }[row.type] }}</template>
      </el-table-column>
      <el-table-column prop="max_guests" label="宜住" width="70" />
      <el-table-column label="状态" width="100">
        <template #default="{ row }">
          <el-tag :type="statusMap[row.status]?.type" size="small">{{ statusMap[row.status]?.label }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="rating" label="评分" width="80" />
      <el-table-column v-if="userStore.isOperator" prop="owner_name" label="房东" width="100" />
      <el-table-column label="操作" width="260" fixed="right">
        <template #default="{ row }">
          <el-button v-if="row.status === 'draft'" text type="primary" @click="openEdit(row)">编辑</el-button>
          <el-button v-if="row.status === 'draft'" text type="primary" @click="submit(row)">提交审核</el-button>
          <template v-if="row.status === 'pending' && userStore.isOperator">
            <el-button text type="success" @click="audit(row, true)">通过</el-button>
            <el-button text type="danger" @click="audit(row, false)">驳回</el-button>
          </template>
          <el-button v-if="row.status === 'online' || row.status === 'offline'" text type="primary"
            @click="router.push(`/admin/listings/${row.id}/calendar`)">日历</el-button>
          <el-button v-if="row.status === 'online' || row.status === 'offline'" text
            :type="row.status === 'online' ? 'danger' : 'success'" @click="toggleOnline(row)">
            {{ row.status === 'online' ? '下架' : '上架' }}
          </el-button>
        </template>
      </el-table-column>
      <template #empty><span class="empty-tip">还没有房源，点击右上角新建</span></template>
    </el-table>

    <!-- 新建/编辑弹窗 -->
    <el-dialog v-model="dialog" :title="editingId ? '编辑房源' : '新建房源'" width="560px">
      <el-form :model="form" label-position="top">
        <el-form-item label="房源标题" required>
          <el-input v-model="form.title" maxlength="100" placeholder="如：大理洱海边的观景 Loft" />
        </el-form-item>
        <div class="form-row">
          <el-form-item label="房源类型" class="half">
            <el-select v-model="form.type">
              <el-option label="整套房源" value="whole" />
              <el-option label="独立房间" value="room" />
              <el-option label="合租间" value="share" />
            </el-select>
          </el-form-item>
          <el-form-item label="可住人数" class="half">
            <el-input-number v-model="form.max_guests" :min="1" :max="10" />
          </el-form-item>
        </div>
        <div class="form-row">
          <el-form-item label="床位数" class="half">
            <el-input-number v-model="form.bed_count" :min="1" :max="10" />
          </el-form-item>
          <el-form-item label="面积(㎡)" class="half">
            <el-input-number v-model="form.area" :min="0" :precision="1" />
          </el-form-item>
        </div>
        <div class="form-row">
          <el-form-item label="城市" class="half">
            <el-input v-model="form.city" placeholder="如：大理" />
          </el-form-item>
          <el-form-item label="区/县" class="half">
            <el-input v-model="form.district" placeholder="如：海东" />
          </el-form-item>
        </div>
        <el-form-item label="详细地址">
          <el-input v-model="form.address" placeholder="房源具体位置（客人确认后可见）" />
        </el-form-item>
        <el-form-item label="默认押金(元)">
          <el-input-number v-model="form.deposit_amount" :min="0" :step="100" />
        </el-form-item>
        <el-form-item label="设施标签">
          <el-input v-model="facilityInput" placeholder="多个标签用逗号分隔，如：海景, 投影仪, 洗衣机" />
        </el-form-item>
        <el-form-item label="房源描述">
          <el-input v-model="form.description" type="textarea" :rows="3" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialog = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="save">保存</el-button>
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

.listing-cell {
  display: flex;
  align-items: center;
  gap: 10px;
}
.thumb {
  width: 72px;
  height: 54px;
  border-radius: 8px;
  object-fit: cover;
  flex-shrink: 0;
}
.t {
  font-size: 14px;
  font-weight: 600;
}
.sub {
  font-size: 12px;
  color: var(--ink-2);
  margin-top: 2px;
}

.empty-tip {
  color: var(--ink-2);
  font-size: 13px;
}

.form-row {
  display: flex;
  gap: 16px;
}
.half {
  flex: 1;
}
</style>
