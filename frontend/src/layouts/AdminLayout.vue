<script setup>
import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useUserStore } from '../stores/user'

/**
 * B 端后台框架：侧边栏 + 顶栏。
 * 菜单按登录用户角色动态过滤（房东看不到派工/查房，保洁只有任务端）。
 */
const router = useRouter()
const route = useRoute()
const userStore = useUserStore()
const collapsed = ref(false)

// 全部菜单及所需角色（与 router meta.roles 对应）
const allMenus = [
  { path: '/admin', icon: 'Odometer', title: '工作台', roles: [] },
  { path: '/admin/listings', icon: 'House', title: '房源管理', roles: ['operator', 'landlord'] },
  { path: '/admin/orders', icon: 'List', title: '订单管理', roles: ['operator', 'landlord'] },
  { path: '/admin/cleaning', icon: 'Brush', title: '清洁任务', roles: ['operator', 'cleaner', 'landlord'] },
  { path: '/admin/repairs', icon: 'Tools', title: '维修工单', roles: ['operator', 'repairer', 'landlord'] },
  { path: '/admin/inspections', icon: 'Search', title: '退房查房', roles: ['operator'] },
  { path: '/admin/settlements', icon: 'Money', title: '结算分账', roles: ['finance', 'operator', 'landlord'] },
  { path: '/admin/stats', icon: 'TrendCharts', title: '经营统计', roles: ['operator', 'landlord'] },
  { path: '/admin/users', icon: 'User', title: '用户管理', roles: ['operator'] },
]

const menus = computed(() => allMenus.filter((m) => m.roles.length === 0
  || m.roles.some((r) => userStore.roles.includes(r))))

const roleLabels = { operator: '运营', landlord: '房东', guest: '客人', cleaner: '保洁', repairer: '维修', finance: '财务' }
const displayName = computed(() => userStore.userInfo?.first_name || userStore.userInfo?.username || '')
const roleText = computed(() => (userStore.roles || []).map((r) => roleLabels[r] || r).join(' / '))

function logout() {
  userStore.logout()
  router.push('/login')
}
</script>

<template>
  <el-container class="admin-layout">
    <el-aside :width="collapsed ? '64px' : '220px'" class="aside">
      <div class="brand" @click="router.push('/admin')">
        <span class="brand-mark">住</span>
        <span v-show="!collapsed" class="brand-text">民宿 PMS</span>
      </div>
      <el-menu :default-active="route.path" :collapse="collapsed" router class="menu">
        <el-menu-item v-for="m in menus" :key="m.path" :index="m.path">
          <el-icon><component :is="m.icon" /></el-icon>
          <template #title>{{ m.title }}</template>
        </el-menu-item>
      </el-menu>
      <div class="collapse-btn" @click="collapsed = !collapsed">
        <el-icon><Expand v-if="collapsed" /><Fold v-else /></el-icon>
      </div>
    </el-aside>

    <el-container>
      <el-header class="header">
        <span class="page-title">{{ route.meta.title || '民宿 PMS 管理后台' }}</span>
        <div class="header-right">
          <el-button text @click="router.push('/')">
            <el-icon><HomeFilled /></el-icon> 访问前台
          </el-button>
          <el-dropdown trigger="click">
            <span class="user-trigger">
              <el-avatar :size="28" :src="userStore.userInfo?.avatar">{{ displayName[0] }}</el-avatar>
              <span>{{ displayName }}（{{ roleText }}）</span>
              <el-icon><ArrowDown /></el-icon>
            </span>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item @click="logout">退出登录</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </el-header>
      <el-main class="main">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<style scoped>
.admin-layout {
  height: 100vh;
}

.aside {
  background: #fff;
  border-right: 1px solid var(--line);
  display: flex;
  flex-direction: column;
  transition: width 0.2s;
}

.brand {
  display: flex;
  align-items: center;
  gap: 10px;
  height: 56px;
  padding: 0 18px;
  cursor: pointer;
  border-bottom: 1px solid var(--line);
}
.brand-mark {
  display: grid;
  place-items: center;
  width: 30px;
  height: 30px;
  border-radius: 8px;
  background: linear-gradient(135deg, var(--brand), #ff8a5b);
  color: #fff;
  font-size: 15px;
  flex-shrink: 0;
}
.brand-text {
  font-weight: 700;
  color: var(--ink);
  white-space: nowrap;
}

.menu {
  border-right: none;
  flex: 1;
  padding: 8px;
}

.collapse-btn {
  height: 44px;
  display: grid;
  place-items: center;
  border-top: 1px solid var(--line);
  color: var(--ink-2);
  cursor: pointer;
}
.collapse-btn:hover {
  color: var(--brand);
}

.header {
  background: #fff;
  border-bottom: 1px solid var(--line);
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.page-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--ink);
}
.header-right {
  display: flex;
  align-items: center;
  gap: 16px;
}
.user-trigger {
  display: flex;
  align-items: center;
  gap: 6px;
  cursor: pointer;
  font-size: 14px;
}

.main {
  background: var(--bg);
  padding: 20px;
}
</style>
