<script setup>
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { register } from '../../api/auth'

const router = useRouter()

const form = reactive({ username: '', phone: '', email: '', password: '', password2: '', role: 'guest' })
const loading = ref(false)

async function onSubmit() {
  if (form.password !== form.password2) {
    ElMessage.warning('两次输入的密码不一致')
    return
  }
  loading.value = true
  try {
    await register(form)
    ElMessage.success('注册成功，请登录')
    router.push('/login')
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
      <h1 class="title">创建账号</h1>
      <p class="subtitle">开启你的民宿之旅</p>

      <el-form :model="form" label-position="top" size="large">
        <el-form-item label="用户名">
          <el-input v-model="form.username" placeholder="请输入用户名" clearable />
        </el-form-item>
        <el-form-item label="手机号">
          <el-input v-model="form.phone" placeholder="请输入手机号" maxlength="11" clearable />
        </el-form-item>
        <el-form-item label="邮箱（选填）">
          <el-input v-model="form.email" placeholder="请输入邮箱" clearable />
        </el-form-item>
        <el-form-item label="密码">
          <el-input v-model="form.password" type="password" placeholder="至少 6 位" show-password />
        </el-form-item>
        <el-form-item label="确认密码">
          <el-input v-model="form.password2" type="password" placeholder="再输一次密码"
            show-password @keyup.enter="onSubmit" />
        </el-form-item>
        <!-- 注册身份：客人与房东可自助注册，其他角色由运营分配 -->
        <el-form-item label="注册身份">
          <el-radio-group v-model="form.role">
            <el-radio-button value="guest">我是客人</el-radio-button>
            <el-radio-button value="landlord">我是房东</el-radio-button>
          </el-radio-group>
        </el-form-item>
        <el-button class="submit" type="primary" size="large" :loading="loading" @click="onSubmit">
          注 册
        </el-button>
      </el-form>

      <p class="switch-tip">已有账号？<router-link to="/login">去登录</router-link></p>
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
