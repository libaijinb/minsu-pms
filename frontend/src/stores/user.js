import { computed, ref } from 'vue'
import { defineStore } from 'pinia'

// 用户状态：token/资料持久化，roles 派生常用判断
export const useUserStore = defineStore('user', () => {
  const token = ref(localStorage.getItem('token') || '')
  const userInfo = ref(JSON.parse(localStorage.getItem('userInfo') || 'null'))

  const isLoggedIn = computed(() => !!token.value)
  const roles = computed(() => userInfo.value?.roles?.map((r) => r.code) || [])
  const isOperator = computed(() => roles.value.includes('operator'))
  const isLandlord = computed(() => roles.value.includes('landlord'))
  const isCleaner = computed(() => roles.value.includes('cleaner'))
  const isRepairer = computed(() => roles.value.includes('repairer'))
  const isFinance = computed(() => roles.value.includes('finance'))

  function setLogin(data) {
    token.value = data.access
    userInfo.value = data.user
    localStorage.setItem('token', data.access)
    localStorage.setItem('userInfo', JSON.stringify(data.user))
  }

  function setUserInfo(info) {
    userInfo.value = info
    localStorage.setItem('userInfo', JSON.stringify(info))
  }

  function logout() {
    token.value = ''
    userInfo.value = null
    localStorage.removeItem('token')
    localStorage.removeItem('userInfo')
  }

  return { token, userInfo, isLoggedIn, roles, isOperator, isLandlord, isCleaner, isRepairer, isFinance, setLogin, setUserInfo, logout }
})
