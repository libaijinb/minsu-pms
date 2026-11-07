<script setup>
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { login } from '../../api/auth'
import { useUserStore } from '../../stores/user'

const router = useRouter()
const userStore = useUserStore()

const form = reactive({ username: '', password: '' })
const loading = ref(false)

// 登录：按角色分流——运营/房东/保洁/维修/财务进后台，客人回前台
async function onSubmit() {
  loading.value = true
  try {
    const data = await login(form)
    userStore.setLogin(data)
    ElMessage.success(`欢迎回来，${data.user.first_name || data.user.username}`)
    const staff = ['operator', 'landlord', 'cleaner', 'repairer', 'finance']
    const isStaff = data.user.roles.some((r) => staff.includes(r.code))
    router.push(isStaff ? '/admin' : '/')
  } catch {
    // 错误提示由拦截器统一弹出
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="auth-page">
    <div class="auth-bg">
      <div class="blob blob-1"></div>
      <div class="blob blob-2"></div>
    </div>

    <el-card class="auth-card lift">
      <div class="brand">
        <span class="brand-mark">住</span>
        <span class="brand-text">民宿 PMS</span>
      </div>
      <h1 class="title">欢迎回来</h1>
      <p class="subtitle">登录后继续你的旅程</p>

      <el-form :model="form" label-position="top" size="large">
        <el-form-item label="用户名">
          <el-input v-model="form.username" placeholder="请输入用户名" clearable />
        </el-form-item>
        <el-form-item label="密码">
          <el-input v-model="form.password" type="password" placeholder="请输入密码"
            show-password @keyup.enter="onSubmit" />
        </el-form-item>
        <el-button class="submit" type="primary" size="large" :loading="loading" @click="onSubmit">
          登 录
        </el-button>
      </el-form>

      <p class="switch-tip">还没有账号？<router-link to="/register">注册一个</router-link></p>
    </el-card>
  </div>
</template>

<style scoped>
.auth-page {
  min-height: 100vh;
  display: grid;
  place-items: center;
  position: relative;
  overflow: hidden;
}

/* 渐变光斑背景，营造消费产品的轻松感 */
.auth-bg {
  position: absolute;
  inset: 0;
  background: linear-gradient(135deg, #fff5f3, #fef9e7);
}
.blob {
  position: absolute;
  border-radius: 50%;
  filter: blur(80px);
  opacity: 0.5;
}
.blob-1 {
  width: 420px;
  height: 420px;
  background: #ffb4a8;
  top: -120px;
  left: -120px;
}
.blob-2 {
  width: 380px;
  height: 380px;
  background: #ffd9a0;
  bottom: -100px;
  right: -100px;
}

.auth-card {
  position: relative;
  width: 100%;
  max-width: 420px;
  border-radius: var(--radius);
  padding: 16px;
  border: none;
}

.brand {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 20px;
}
.brand-mark {
  display: grid;
  place-items: center;
  width: 34px;
  height: 34px;
  border-radius: 10px;
  background: linear-gradient(135deg, var(--brand), #ff8a5b);
  color: #fff;
  font-size: 17px;
}
.brand-text {
  font-weight: 700;
  font-size: 17px;
}

.title {
  font-size: 26px;
  color: var(--ink);
}
.subtitle {
  color: var(--ink-2);
  font-size: 14px;
  margin: 4px 0 24px;
}

.submit {
  width: 100%;
  margin-top: 4px;
  font-weight: 600;
}

.switch-tip {
  text-align: center;
  font-size: 13px;
  color: var(--ink-2);
  margin-top: 18px;
}
</style>
