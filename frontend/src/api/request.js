import axios from 'axios'
import { ElMessage } from 'element-plus'
import { useUserStore } from '../stores/user'

const request = axios.create({
  baseURL: '/api',
  timeout: 15000,  // 月结等重接口放宽到 15 秒
})

// 请求拦截器：自动带 JWT
request.interceptors.request.use((config) => {
  const userStore = useUserStore()
  if (userStore.token) {
    config.headers.Authorization = `Bearer ${userStore.token}`
  }
  return config
})

// 响应拦截器：统一处理 401 与错误提示
request.interceptors.response.use(
  (res) => res.data,
  (error) => {
    const status = error.response?.status
    if (status === 401) {
      const userStore = useUserStore()
      userStore.logout()
      ElMessage.error('登录已过期，请重新登录')
      if (!location.hash.startsWith('#/login')) {
        location.hash = '#/login'
      }
    } else if (error.response?.data) {
      const data = error.response.data
      const msg = typeof data === 'string'
        ? data
        : data.detail || Object.values(data).flat().join('；')
      ElMessage.error(msg || '请求失败')
    } else {
      ElMessage.error('网络异常，请稍后重试')
    }
    return Promise.reject(error)
  }
)

export default request
