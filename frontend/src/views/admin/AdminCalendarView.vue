<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import dayjs from 'dayjs'
import {
  batchPrice, closeDates, createPriceRule, deletePriceRule,
  listListings, listPriceRules, openDates,
} from '../../api/listings'
import PriceCalendar from '../../components/PriceCalendar.vue'

/**
 * 日历管理（房东/运营）：PMS 的发动机页面——
 * ① 切换房源（房东默认只有自己的）
 * ② 日历视图（复用 PriceCalendar 展示）
 * ③ 批量改价：选日期区间 + 价格，只改可订晚（BR-CAL-08）
 * ④ 关房/开房：多选日期，自留或停售
 * ⑤ 价格规则：基础价/周末价/节假日/指定日期/连住折扣
 */
const route = useRoute()

const listings = ref([])
const currentId = ref(Number(route.params.id) || '')
const loading = ref(false)

const priceForm = reactive({ range: [], start: '', end: '', price: null })
const closeForm = reactive({ dates: [], reason: '房东自留' })
const rules = ref([])
const ruleDialog = ref(false)
const ruleForm = reactive({ type: 'base', price: null, date: '', start_date: '', end_date: '', min_nights: null, discount_rate: null })

const ruleTypeLabel = { base: '基础价', weekend: '周末价', holiday: '节假日价', special_date: '指定日期价', longstay: '连住折扣' }

async function loadListings() {
  const data = await listListings({ page_size: 50 })
  listings.value = data.results || []
  if (!currentId.value && listings.value.length) currentId.value = listings.value[0].id
}

async function loadRules() {
  if (!currentId.value) return
  const data = await listPriceRules({ listing: currentId.value, page_size: 50 })
  rules.value = data.results || []
}

async function doBatchPrice() {
  if (!priceForm.start || !priceForm.end || !priceForm.price) {
    ElMessage.warning('请填写完整的起止日期和价格')
    return
  }
  const res = await batchPrice(currentId.value, { start: priceForm.start, end: priceForm.end, price: priceForm.price })
  ElMessage.success(res.detail)
  priceForm.price = null
}

async function doCloseDates() {
  if (!closeForm.dates.length) {
    ElMessage.warning('请选择要关闭的日期')
    return
  }
  const dates = closeForm.dates.map((d) => dayjs(d).format('YYYY-MM-DD'))
  const res = await closeDates(currentId.value, dates, closeForm.reason)
  ElMessage.success(res.detail)
  closeForm.dates = []
}

async function doOpenDates() {
  if (!closeForm.dates.length) {
    ElMessage.warning('请选择要打开的日期')
    return
  }
  const dates = closeForm.dates.map((d) => dayjs(d).format('YYYY-MM-DD'))
  const res = await openDates(currentId.value, dates)
  ElMessage.success(res.detail)
  closeForm.dates = []
}

function openRuleDialog() {
  Object.assign(ruleForm, { type: 'base', price: null, date: '', start_date: '', end_date: '', min_nights: null, discount_rate: null })
  ruleDialog.value = true
}

async function saveRule() {
  await createPriceRule({ ...ruleForm, listing: currentId.value })
  ElMessage.success('规则已保存')
  ruleDialog.value = false
  loadRules()
}

async function removeRule(id) {
  await deletePriceRule(id)
  ElMessage.success('规则已删除')
  loadRules()
}

function onListingChange() {
  loadRules()
}

onMounted(async () => {
  loading.value = true
  try {
    await loadListings()
    await loadRules()
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div v-loading="loading" class="page">
    <div class="toolbar">
      <h2 class="page-title">日历与价格</h2>
      <el-select v-model="currentId" style="width: 280px" @change="onListingChange">
        <el-option v-for="l in listings" :key="l.id" :label="`${l.title}（${l.city}）`" :value="l.id" />
      </el-select>
    </div>

    <div class="layout">
      <!-- 日历视图 -->
      <div class="card calendar-card">
        <h3>房态日历</h3>
        <PriceCalendar v-if="currentId" :listing-id="currentId" :months="2" />
      </div>

      <div class="side-col">
        <!-- 批量改价 -->
        <div class="card">
          <h3>批量改价</h3>
          <p class="hint">只修改「可订」状态的晚；已订/锁定晚自动跳过</p>
          <div class="form-item">
            <label>日期区间</label>
            <el-date-picker v-model="priceForm.range" type="daterange" value-format="YYYY-MM-DD"
              start-placeholder="开始" end-placeholder="结束" style="width: 100%"
              @change="(v) => { priceForm.start = v?.[0] || ''; priceForm.end = v?.[1] || '' }" />
          </div>
          <div class="form-item">
            <label>每晚价格(元)</label>
            <el-input-number v-model="priceForm.price" :min="1" :step="50" style="width: 100%" />
          </div>
          <el-button class="block" type="primary" round @click="doBatchPrice">应用改价</el-button>
        </div>

        <!-- 关房/开房 -->
        <div class="card">
          <h3>关房 / 开房</h3>
          <p class="hint">关闭后客人不可预订；维修或自留场景使用</p>
          <div class="form-item">
            <label>选择日期（可多选）</label>
            <el-date-picker v-model="closeForm.dates" type="dates" value-format="YYYY-MM-DD"
              placeholder="点击选择多个日期" style="width: 100%" />
          </div>
          <div class="form-item">
            <label>关闭原因</label>
            <el-input v-model="closeForm.reason" placeholder="如：房东自留" />
          </div>
          <div class="btn-row">
            <el-button type="danger" round @click="doCloseDates">关闭所选</el-button>
            <el-button round @click="doOpenDates">打开所选</el-button>
          </div>
        </div>

        <!-- 价格规则 -->
        <div class="card">
          <div class="card-head">
            <h3>价格规则</h3>
            <el-button text type="primary" @click="openRuleDialog">+ 添加</el-button>
          </div>
          <el-table :data="rules" size="small" empty-text="暂无规则">
            <el-table-column label="类型" width="100">
              <template #default="{ row }">{{ ruleTypeLabel[row.type] }}</template>
            </el-table-column>
            <el-table-column label="内容">
              <template #default="{ row }">
                <span v-if="row.type === 'base'">¥{{ row.price }}</span>
                <span v-else-if="row.type === 'weekend'">¥{{ row.price }}</span>
                <span v-else-if="row.type === 'special_date'">{{ row.date }} · ¥{{ row.price }}</span>
                <span v-else-if="row.type === 'holiday'">{{ row.start_date }} ~ {{ row.end_date }} · ¥{{ row.price }}</span>
                <span v-else-if="row.type === 'longstay'">住满 {{ row.min_nights }} 晚 {{ row.discount_rate * 10 }} 折</span>
              </template>
            </el-table-column>
            <el-table-column label="" width="56">
              <template #default="{ row }">
                <el-button text type="danger" size="small" @click="removeRule(row.id)">删</el-button>
              </template>
            </el-table-column>
          </el-table>
        </div>
      </div>
    </div>

    <!-- 价格规则弹窗：按类型动态显示字段 -->
    <el-dialog v-model="ruleDialog" title="添加价格规则" width="460px">
      <el-form :model="ruleForm" label-position="top">
        <el-form-item label="规则类型">
          <el-select v-model="ruleForm.type" style="width: 100%">
            <el-option v-for="(label, key) in ruleTypeLabel" :key="key" :label="label" :value="key" />
          </el-select>
        </el-form-item>
        <el-form-item v-if="ruleForm.type !== 'longstay'" label="价格(元)">
          <el-input-number v-model="ruleForm.price" :min="1" style="width: 100%" />
        </el-form-item>
        <el-form-item v-if="ruleForm.type === 'special_date'" label="指定日期">
          <el-date-picker v-model="ruleForm.date" type="date" value-format="YYYY-MM-DD" style="width: 100%" />
        </el-form-item>
        <template v-if="ruleForm.type === 'holiday'">
          <el-form-item label="开始日期">
            <el-date-picker v-model="ruleForm.start_date" type="date" value-format="YYYY-MM-DD" style="width: 100%" />
          </el-form-item>
          <el-form-item label="结束日期">
            <el-date-picker v-model="ruleForm.end_date" type="date" value-format="YYYY-MM-DD" style="width: 100%" />
          </el-form-item>
        </template>
        <template v-if="ruleForm.type === 'longstay'">
          <el-form-item label="最少连住晚数">
            <el-input-number v-model="ruleForm.min_nights" :min="2" style="width: 100%" />
          </el-form-item>
          <el-form-item label="折扣率（0.9 = 9 折）">
            <el-input-number v-model="ruleForm.discount_rate" :min="0.1" :max="1" :step="0.05" style="width: 100%" />
          </el-form-item>
        </template>
      </el-form>
      <template #footer>
        <el-button @click="ruleDialog = false">取消</el-button>
        <el-button type="primary" @click="saveRule">保存</el-button>
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

.layout {
  display: grid;
  grid-template-columns: 1fr 360px;
  gap: 16px;
  align-items: start;
}

.card {
  background: #fff;
  border-radius: 14px;
  box-shadow: var(--shadow);
  padding: 18px;
  margin-bottom: 16px;
}
.card h3 {
  font-size: 15px;
  margin-bottom: 10px;
}
.calendar-card {
  padding: 24px;
}

.card-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.hint {
  font-size: 12px;
  color: var(--ink-2);
  margin-bottom: 10px;
}

.form-item {
  margin-bottom: 12px;
}
.form-item label {
  display: block;
  font-size: 12px;
  color: var(--ink-2);
  font-weight: 600;
  margin-bottom: 4px;
}

.block {
  width: 100%;
}
.btn-row {
  display: flex;
  gap: 10px;
}
.btn-row .el-button {
  flex: 1;
}

@media (max-width: 1000px) {
  .layout {
    grid-template-columns: 1fr;
  }
}
</style>
