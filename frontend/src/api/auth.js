import request from './request'

// 认证与用户
export const register = (data) => request.post('/auth/register/', data)       // 注册（role: guest/landlord）
export const login = (data) => request.post('/auth/login/', data)             // 登录
export const getMe = () => request.get('/auth/me/')                           // 我的资料
export const updateMe = (data) => request.patch('/auth/me/', data)            // 修改资料
export const changePassword = (data) => request.post('/auth/password/', data) // 改密码
export const listRoles = () => request.get('/auth/roles/')                    // 角色列表
export const listUsers = (params) => request.get('/users/', { params })       // 用户列表（运营）
export const assignRoles = (id, roles) => request.post(`/users/${id}/roles/`, { roles })  // 分配角色
