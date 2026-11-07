<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '../../stores/user'
import { listOrders } from '../../api/orders'
import { listCleaningTasks } from '../../api/services'
import { listInspections } from '../../api/orders'
import { listSettlements } from '../../api/finance'
import { listListings } from '../../api/listings'

/**
 * 工作台：按角色聚合计办数字 + 快捷入口。
 * 运营关心待确认/待派工/待查房；房东关心房源与订单；保洁看今日任务；财务看待分账。
 */
const router = useRouter()
const userStore = useUserStore()

const stats = ref({
  pendingConfirm: 0, pendingCleaning: 0, pendingInspection: 0,
  pendingPayout: 0, myListings: 0, myTodayTasks: 0,
})
const loading = ref(false)

const roleLabels = { operator: '运营', landlord: '房东', guest: '客人', cleaner: '保洁', repairer: '维修', finance: '财务' }
const greeting = computed(() => `你好，${userStore.userInfo?.first_name || userStore.userInfo?.username}`)
const roleText = computed(() => (userStore.roles || []).map((r) => roleLabels[r] || r).join(' / '))

// 快捷入口（与角色菜单一致的子集）
const entries = [
  { path: '/admin/listings', title: '房源管理', desc: '上架/改价/关房', icon: 'House', roles: ['operator', 'landlord'] },
  { path: '/admin/orders', title: '订单管理', desc: '确认/入住/退房', icon: 'List', roles: ['operator', 'landlord'] },
  { path: '/admin/cleaning', title: '清洁任务', desc: '派工/完成/复核', icon: 'Brush', roles: ['operator', 'cleaner', 'landlord'] },
  { path: '/admin/repairs', title: '维修工单', desc: '派工/处理/验收', icon: 'Tools', roles: ['operator', 'repairer', 'landlord'] },
  { path: '/admin/inspections', title: '退房查房', desc: '定损/押金扣减', icon: 'Search', roles: ['operator'] },
  { path: '/admin/settlements', title: '结算分账', desc: '月结/分账/重试', icon: 'Money', roles: ['finance', 'operator', 'landlord'] },
  { path: '/admin/stats', title: '经营统计', desc: 'OCC/ADR/RevPAR', icon: 'TrendCharts', roles: ['operator', 'landlord'] },
  { path: '/admin/users', title: '用户管理', desc: '角色分配', icon: 'User', roles: ['operator'] },
]
const myEntries = computed(() => entries.filter((e) => e.roles.some((r) => userStore.roles.includes(r))))

async function loadStats() {
  loading.value = true
  try {
    const tasks = []
    if (userStore.isOperator || userStore.isLandlord) {
      tasks.push(listOrders({ status: 'pending_confirm', page_size: 1 }).then((d) => {
        stats.value.pendingConfirm = d.count
      }))
      tasks.push(listListings({ page_size: 1 }).then((d) => {
        stats.value.myListings = d.count
      }))
    }
    if (userStore.isOperator) {
      tasks.push(listCleaningTasks({ page_size: 100 }).then((d) => {
        stats.value.pendingCleaning = d.results.filter((t) => t.status === 'pending').length
      }))
      tasks.push(listInspections({ status: 'todo' }).then((d) => {
        stats.value.pendingInspection = Array.isArray(d) ? d.length : 0
      }))
    }
    if (userStore.isCleaner) {
      tasks.push(listCleaningTasks({ page_size: 100 }).then((d) => {
        stats.value.myTodayTasks = d.results.filter((t) =>
          t.cleaner === userStore.userInfo?.id && t.status === 'assigned').length
      }))
    }
    if (userStore.isFinance || userStore.isOperator) {
      tasks.push(listSettlements({ page_size: 100 }).then((d) => {
        stats.value.pendingPayout = d.results.filter((s) => s.status !== 'paid').length
      }))
    }
    await Promise.all(tasks)
  } finally {
    loading.value = false
  }
}

onMounted(loadStats)
</script>

<template>
  <div v-loading="loading" class="dashboard">
    <!-- 欢迎卡 -->
    <div class="welcome">
      <div>
        <h2>{{ greeting }}</h2>
        <p class="role-line">当前身份：{{ roleText }}</p>
      </div>
      <el-button type="primary" round @click="router.push('/')">访问前台</el-button>
    </div>

    <!-- 待办数字（按角色显示对应卡片） -->
    <div class="stat-grid">
      <div v-if="userStore.isOperator || userStore.isLandlord" class="stat-card" @click="router.push('/admin/orders?status=pending_confirm')">
        <span class="num warning">{{ stats.pendingConfirm }}</span>
        <span class="label">待确认订单</span>
      </div>
      <div v-if="userStore.isOperator" class="stat-card" @click="router.push('/admin/cleaning')">
        <span class="num warning">{{ stats.pendingCleaning }}</span>
        <span class="label">待派工清洁</span>
      </div>
      <div v-if="userStore.isOperator" class="stat-card" @click="router.push('/admin/inspections')">
        <span class="num warning">{{ stats.pendingInspection }}</span>
        <span class="label">待查房</span>
      </div>
      <div v-if="userStore.isFinance || userStore.isOperator" class="stat-card" @click="router.push('/admin/settlements')">
        <span class="num warning">{{ stats.pendingPayout }}</span>
        <span class="label">待分账结算</span>
      </div>
      <div v-if="userStore.isCleaner" class="stat-card" @click="router.push('/admin/cleaning')">
        <span class="num primary">{{ stats.myTodayTasks }}</span>
        <span class="label">我的待办任务</span>
      </div>
      <div v-if="userStore.isOperator || userStore.isLandlord" class="stat-card" @click="router.push('/admin/listings')">
        <span class="num primary">{{ stats.myListings }}</span>
        <span class="label">房源总数</span>
      </div>
    </div>

    <!-- 快捷入口 -->
    <h3 class="section-title">快捷入口</h3>
    <div class="entry-grid">
      <div v-for="e in myEntries" :key="e.path" class="entry-card lift" @click="router.push(e.path)">
        <div class="entry-icon"><el-icon :size="22"><component :is="e.icon" /></el-icon></div>
        <div>
          <p class="entry-title">{{ e.title }}</p>
          <p class="entry-desc">{{ e.desc }}</p>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.welcome {
  background: linear-gradient(135deg, #fff, #fff5f3);
  border: 1px solid var(--line);
  border-radius: var(--radius);
  padding: 24px 28px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}
.welcome h2 {
  font-size: 20px;
}
.role-line {
  font-size: 13px;
  color: var(--ink-2);
  margin-top: 4px;
}

.stat-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
  gap: 14px;
  margin-bottom: 24px;
}
.stat-card {
  background: #fff;
  border-radius: 14px;
  box-shadow: var(--shadow);
  padding: 18px;
  cursor: pointer;
  transition: transform 0.2s;
}
.stat-card:hover {
  transform: translateY(-3px);
}
.num {
  display: block;
  font-size: 28px;
  font-weight: 800;
}
.num.warning {
  color: #d97706;
}
.num.primary {
  color: var(--brand);
}
.label {
  font-size: 13px;
  color: var(--ink-2);
  margin-top: 2px;
  display: block;
}

.section-title {
  font-size: 16px;
  margin-bottom: 14px;
}

.entry-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(230px, 1fr));
  gap: 14px;
}
.entry-card {
  display: flex;
  align-items: center;
  gap: 14px;
  background: #fff;
  border-radius: 14px;
  box-shadow: var(--shadow);
  padding: 16px 18px;
  cursor: pointer;
}
.entry-icon {
  width: 44px;
  height: 44px;
  border-radius: 12px;
  background: var(--brand-light);
  color: var(--brand);
  display: grid;
  place-items: center;
  flex-shrink: 0;
}
.entry-title {
  font-weight: 700;
  font-size: 14px;
}
.entry-desc {
  font-size: 12px;
  color: var(--ink-2);
  margin-top: 2px;
}
</style>
