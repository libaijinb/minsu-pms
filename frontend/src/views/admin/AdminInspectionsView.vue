<script setup>
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { listInspections, submitInspection } from '../../api/orders'

/**
 * 退房查房（运营）：
 * - 待查房列表 = 已退房且无查房记录的订单（后端查询表达，不建表）
 * - 提交查房：逐项登记（正常/损坏+定损金额）→ 损坏项自动生成维修工单 + 押金扣减（BR-INS/REP-02）
 */
const todoList = ref([])
const doneList = ref([])
const loading = ref(false)
const dialog = ref(false)
const current = ref(null)

// 查房表单：items 可增删行
const items = ref([{ name: '卧室卫生', result: 'normal', note: '', amount: 0 }])
const defaultItems = ['卧室卫生', '厨房卫生', '卫生间卫生', '家具完好', '家电完好', '布草/床品']

async function loadData() {
  loading.value = true
  try {
    const [todo, done] = await Promise.all([
      listInspections({ status: 'todo' }),
      listInspections({ status: 'done' }),
    ])
    todoList.value = todo
    doneList.value = done
  } finally {
    loading.value = false
  }
}

function openSubmit(row) {
  current.value = row
  // 预置检查项模板，运营逐项改结果
  items.value = defaultItems.map((name) => ({ name, result: 'normal', note: '', amount: 0 }))
  dialog.value = true
}

function addItem() {
  items.value.push({ name: '', result: 'normal', note: '', amount: 0 })
}

function removeItem(idx) {
  items.value.splice(idx, 1)
}

const damageTotal = computed(() =>
  items.value.filter((i) => i.result === 'damage').reduce((s, i) => s + Number(i.amount || 0), 0))

async function submit() {
  const payload = {
    order_no: current.value.order_no,
    items: items.value.filter((i) => i.name),
  }
  await submitInspection(payload)
  ElMessage.success(`查房完成，定损 ¥${damageTotal.value}，押金扣减与维修工单已自动生成`)
  dialog.value = false
  loadData()
}

onMounted(loadData)
</script>

<template>
  <div v-loading="loading" class="page">
    <h2 class="page-title">退房查房</h2>

    <h3 class="section-title">待查房（{{ todoList.length }}）</h3>
    <el-table :data="todoList" stripe empty-text="暂无待查房订单">
      <el-table-column prop="order_no" label="订单号" width="180" />
      <el-table-column prop="listing_title" label="房源" min-width="160" show-overflow-tooltip />
      <el-table-column prop="guest_name" label="客人" width="90" />
      <el-table-column prop="checkout_date" label="退房日期" width="130" />
      <el-table-column label="押金" width="100">
        <template #default="{ row }">¥{{ row.has_deposit }}（{{ row.deposit_status }}）</template>
      </el-table-column>
      <el-table-column label="操作" width="120">
        <template #default="{ row }">
          <el-button text type="primary" @click="openSubmit(row)">去查房</el-button>
        </template>
      </el-table-column>
    </el-table>

    <h3 class="section-title">查房记录</h3>
    <el-table :data="doneList" stripe empty-text="暂无查房记录">
      <el-table-column prop="order_no" label="订单号" width="180" />
      <el-table-column label="结论" width="90">
        <template #default="{ row }">
          <el-tag :type="row.conclusion === 'pass' ? 'success' : 'danger'" size="small">
            {{ row.conclusion_display }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="damage_total" label="定损金额" width="100">
        <template #default="{ row }">¥{{ row.damage_total }}</template>
      </el-table-column>
      <el-table-column prop="inspector_name" label="查房人" width="90" />
      <el-table-column prop="created_at" label="查房时间" min-width="160" />
    </el-table>

    <!-- 查房弹窗 -->
    <el-dialog v-model="dialog" title="退房查房登记" width="640px">
      <template v-if="current">
        <p class="dialog-meta">
          订单 {{ current.order_no }} · {{ current.listing_title }} · 押金 ¥{{ current.has_deposit }}
        </p>
        <el-table :data="items" size="small" class="items-table">
          <el-table-column label="检查项" min-width="140">
            <template #default="{ row, $index }">
              <el-input v-model="row.name" size="small" placeholder="检查项名称" />
            </template>
          </el-table-column>
          <el-table-column label="结果" width="130">
            <template #default="{ row }">
              <el-select v-model="row.result" size="small">
                <el-option label="正常" value="normal" />
                <el-option label="损坏" value="damage" />
              </el-select>
            </template>
          </el-table-column>
          <el-table-column label="定损(元)" width="110">
            <template #default="{ row }">
              <el-input-number v-model="row.amount" size="small" :min="0" :disabled="row.result !== 'damage'" />
            </template>
          </el-table-column>
          <el-table-column label="备注" min-width="140">
            <template #default="{ row }">
              <el-input v-model="row.note" size="small" placeholder="选填" />
            </template>
          </el-table-column>
          <el-table-column width="44">
            <template #default="{ $index }">
              <el-button text type="danger" size="small" @click="removeItem($index)">×</el-button>
            </template>
          </el-table-column>
        </el-table>
        <div class="dialog-footer-row">
          <el-button text type="primary" @click="addItem">+ 添加检查项</el-button>
          <span class="damage-total">定损合计：<b>¥{{ damageTotal }}</b></span>
        </div>
        <p class="dialog-tip">
          提交后：损坏项自动生成维修工单，并从押金中扣减对应金额（BR-INS-04）
        </p>
      </template>
      <template #footer>
        <el-button @click="dialog = false">取消</el-button>
        <el-button type="primary" @click="submit">提交查房结果</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.page-title {
  font-size: 18px;
  font-weight: 700;
  margin-bottom: 16px;
}
.section-title {
  font-size: 15px;
  margin: 20px 0 12px;
}

.dialog-meta {
  font-size: 13px;
  color: var(--ink-2);
  margin-bottom: 12px;
}
.items-table {
  margin-bottom: 8px;
}
.dialog-footer-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 8px;
}
.damage-total {
  font-size: 14px;
}
.damage-total b {
  color: var(--brand);
  font-size: 16px;
}
.dialog-tip {
  font-size: 12px;
  color: var(--ink-2);
  background: #fef3c7;
  border-radius: 8px;
  padding: 8px 12px;
  margin-top: 12px;
}
</style>
