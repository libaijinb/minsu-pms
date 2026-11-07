<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '../stores/user'

/**
 * C 端框架：现代消费网站三件套——
 * ① 顶部导航滚动时从透明变毛玻璃（backdrop-filter）
 * ② 品牌 Logo + 主菜单 + 右侧登录态/后台入口
 * ③ 移动端抽屉菜单
 */
const router = useRouter()
const userStore = useUserStore()
const scrolled = ref(false)
const drawer = ref(false)
const unread = ref(0)

function onScroll() {
  scrolled.value = window.scrollY > 24
}
onMounted(() => window.addEventListener('scroll', onScroll, { passive: true }))
onUnmounted(() => window.removeEventListener('scroll', onScroll))

const displayName = computed(() => userStore.userInfo?.first_name || userStore.userInfo?.username || '')
const hasStaffRole = computed(() => userStore.roles.some((r) =>
  ['operator', 'landlord', 'cleaner', 'repairer', 'finance'].includes(r)))

function logout() {
  userStore.logout()
  router.push('/login')
}
</script>

<template>
  <div class="guest-layout">
    <header class="nav" :class="{ scrolled }">
      <div class="container nav-inner">
        <router-link to="/" class="logo">
          <span class="logo-mark">住</span>
          <span class="logo-text">民宿 PMS</span>
        </router-link>

        <nav class="menu">
          <router-link to="/" exact-active-class="active">发现房源</router-link>
          <router-link v-if="userStore.isLoggedIn" to="/my/orders" active-class="active">我的订单</router-link>
        </nav>

        <div class="actions">
          <template v-if="userStore.isLoggedIn">
            <el-badge :value="unread" :hidden="unread === 0" class="bell">
              <el-button text circle @click="router.push('/my/orders')">
                <el-icon><Bell /></el-icon>
              </el-button>
            </el-badge>
            <el-dropdown trigger="click">
              <span class="user-trigger">
                <el-avatar :size="30" :src="userStore.userInfo?.avatar">{{ displayName[0] }}</el-avatar>
                <span class="user-name">{{ displayName }}</span>
                <el-icon><ArrowDown /></el-icon>
              </span>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item @click="router.push('/my/orders')">我的订单</el-dropdown-item>
                  <el-dropdown-item v-if="hasStaffRole" @click="router.push('/admin')">进入管理后台</el-dropdown-item>
                  <el-dropdown-item divided @click="logout">退出登录</el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </template>
          <template v-else>
            <el-button text class="login-btn" @click="router.push('/login')">登录</el-button>
            <el-button class="register-btn" round @click="router.push('/register')">注册</el-button>
          </template>
          <el-icon class="drawer-toggle" @click="drawer = true"><Fold /></el-icon>
        </div>
      </div>
    </header>

    <main>
      <router-view />
    </main>

    <footer class="footer">
      <div class="container footer-inner">
        <span>民宿 PMS · 发现美好的住</span>
        <span class="footer-sub">Django DRF + Vue3 前后端分离实践项目</span>
      </div>
    </footer>

    <!-- 移动端抽屉 -->
    <el-drawer v-model="drawer" direction="rtl" size="70%">
      <template #header><span class="logo-text">菜单</span></template>
      <router-link to="/" @click="drawer = false">发现房源</router-link>
      <router-link v-if="userStore.isLoggedIn" to="/my/orders" @click="drawer = false">我的订单</router-link>
      <router-link v-if="hasStaffRole" to="/admin" @click="drawer = false">管理后台</router-link>
    </el-drawer>
  </div>
</template>

<style scoped>
.nav {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  z-index: 100;
  transition: background 0.3s ease, box-shadow 0.3s ease, backdrop-filter 0.3s ease;
}
.nav.scrolled {
  background: rgba(255, 255, 255, 0.85);
  backdrop-filter: blur(12px);
  box-shadow: 0 1px 0 var(--line);
}

.nav-inner {
  display: flex;
  align-items: center;
  height: 64px;
  gap: 32px;
}

.logo {
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--ink);
  font-weight: 700;
}
.logo-mark {
  display: grid;
  place-items: center;
  width: 32px;
  height: 32px;
  border-radius: 10px;
  background: linear-gradient(135deg, var(--brand), #ff8a5b);
  color: #fff;
  font-size: 16px;
}
.logo-text {
  font-size: 17px;
  letter-spacing: 0.5px;
}

.menu {
  display: flex;
  gap: 24px;
  flex: 1;
}
.menu a {
  color: var(--ink-2);
  font-size: 15px;
  padding: 4px 0;
  border-bottom: 2px solid transparent;
  transition: color 0.2s, border-color 0.2s;
}
.menu a:hover,
.menu a.active {
  color: var(--ink);
  border-color: var(--brand);
}

.actions {
  display: flex;
  align-items: center;
  gap: 12px;
}
.user-trigger {
  display: flex;
  align-items: center;
  gap: 6px;
  cursor: pointer;
  color: var(--ink);
}
.user-name {
  font-size: 14px;
}
.login-btn {
  color: var(--ink);
}
.register-btn {
  background: var(--brand);
  border-color: var(--brand);
  color: #fff;
}
.register-btn:hover {
  background: var(--brand-dark);
  border-color: var(--brand-dark);
}

.drawer-toggle {
  display: none;
  font-size: 22px;
  cursor: pointer;
}

main {
  padding-top: 64px;  /* 给固定导航让位 */
  min-height: calc(100vh - 160px);
}

.footer {
  border-top: 1px solid var(--line);
  background: #fff;
  padding: 28px 0;
}
.footer-inner {
  display: flex;
  justify-content: space-between;
  align-items: center;
  color: var(--ink-2);
  font-size: 13px;
}
.footer-sub {
  opacity: 0.7;
}

@media (max-width: 768px) {
  .menu,
  .user-name {
    display: none;
  }
  .drawer-toggle {
    display: block;
  }
}
</style>
