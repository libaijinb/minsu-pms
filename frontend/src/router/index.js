import { createRouter, createWebHashHistory } from 'vue-router'
import { useUserStore } from '../stores/user'

/**
 * 路由分两类气质：
 * - C 端（guest/*）：现代化消费界面，毛玻璃导航 + 大图卡片
 * - B 端（admin/*）：Element Plus 工具风，侧边栏菜单按角色动态过滤
 * meta.auth 要求登录；meta.roles 要求拥有指定角色之一
 */
const routes = [
  // 认证
  { path: '/login', name: 'login', component: () => import('../views/auth/LoginView.vue'), meta: { guest: true } },
  { path: '/register', name: 'register', component: () => import('../views/auth/RegisterView.vue'), meta: { guest: true } },

  // C 端客人（GuestLayout 框架：毛玻璃导航 + 页脚）
  {
    path: '/',
    component: () => import('../layouts/GuestLayout.vue'),
    children: [
      { path: '', name: 'home', component: () => import('../views/guest/HomeView.vue') },
      { path: 'listing/:id', name: 'listing-detail', component: () => import('../views/guest/ListingDetailView.vue') },
      { path: 'booking/:id', name: 'booking', component: () => import('../views/guest/BookingView.vue'), meta: { auth: true } },
      { path: 'my/orders', name: 'my-orders', component: () => import('../views/guest/MyOrdersView.vue'), meta: { auth: true } },
    ],
  },

  // B 端后台（六角色共用一套框架，菜单按角色过滤）
  {
    path: '/admin',
    component: () => import('../layouts/AdminLayout.vue'),
    meta: { auth: true, staff: true },  // staff = 拥有任一运营/房东/保洁/维修/财务角色
    children: [
      { path: '', name: 'dashboard', component: () => import('../views/admin/DashboardView.vue') },
      { path: 'listings', name: 'admin-listings', component: () => import('../views/admin/AdminListingsView.vue'), meta: { roles: ['operator', 'landlord'] } },
      { path: 'listings/:id/calendar', name: 'admin-calendar', component: () => import('../views/admin/AdminCalendarView.vue'), meta: { roles: ['operator', 'landlord'] } },
      { path: 'orders', name: 'admin-orders', component: () => import('../views/admin/AdminOrdersView.vue'), meta: { roles: ['operator', 'landlord'] } },
      { path: 'cleaning', name: 'admin-cleaning', component: () => import('../views/admin/AdminCleaningView.vue'), meta: { roles: ['operator', 'cleaner', 'landlord'] } },
      { path: 'repairs', name: 'admin-repairs', component: () => import('../views/admin/AdminRepairsView.vue'), meta: { roles: ['operator', 'repairer', 'landlord'] } },
      { path: 'inspections', name: 'admin-inspections', component: () => import('../views/admin/AdminInspectionsView.vue'), meta: { roles: ['operator'] } },
      { path: 'settlements', name: 'admin-settlements', component: () => import('../views/admin/AdminSettlementsView.vue'), meta: { roles: ['finance', 'operator', 'landlord'] } },
      { path: 'stats', name: 'admin-stats', component: () => import('../views/admin/AdminStatsView.vue'), meta: { roles: ['operator', 'landlord'] } },
      { path: 'users', name: 'admin-users', component: () => import('../views/admin/AdminUsersView.vue'), meta: { roles: ['operator'] } },
    ],
  },
]

const router = createRouter({
  history: createWebHashHistory(),
  routes,
  scrollBehavior: () => ({ top: 0 }),
})

const STAFF_ROLES = ['operator', 'landlord', 'cleaner', 'repairer', 'finance']

router.beforeEach((to) => {
  const userStore = useUserStore()
  if (to.meta.auth && !userStore.isLoggedIn) return '/login'
  if (to.meta.guest && userStore.isLoggedIn) return '/'
  if (to.meta.staff && !userStore.roles.some((r) => STAFF_ROLES.includes(r))) {
    return '/'  // 纯客人角色不给进后台
  }
  if (to.meta.roles && !to.meta.roles.some((r) => userStore.roles.includes(r))) {
    return '/admin'  // 角色不匹配的具体页面退回工作台
  }
})

export default router
