import request from './request'

// 清洁任务
export const listCleaningTasks = (params) => request.get('/cleaning-tasks/', { params })
export const assignCleaningTask = (id, data) => request.post(`/cleaning-tasks/${id}/assign/`, data)
export const finishCleaningTask = (id, photos) => request.post(`/cleaning-tasks/${id}/finish/`, { photos })
export const reviewCleaningTask = (id) => request.post(`/cleaning-tasks/${id}/review/`)

// 维修工单
export const listRepairTickets = (params) => request.get('/repair-tickets/', { params })
export const createRepairTicket = (data) => request.post('/repair-tickets/', data)
export const assignRepairTicket = (id, repairer) => request.post(`/repair-tickets/${id}/assign/`, { repairer })
export const handleRepairTicket = (id, data) => request.post(`/repair-tickets/${id}/handle/`, data)
export const closeRepairTicket = (id) => request.post(`/repair-tickets/${id}/close/`)
