import request from './request'

// 评价/站内信/统计
export const listReviews = (params) => request.get('/reviews/', { params })
export const createReview = (data) => request.post('/reviews/', data)
export const replyReview = (id, reply) => request.post(`/reviews/${id}/reply/`, { reply })
export const listNotifications = (params) => request.get('/notifications/', { params })
export const readNotification = (id) => request.post(`/notifications/${id}/read/`)
export const readAllNotifications = () => request.post('/notifications/read-all/')
export const getStats = () => request.get('/stats/overview/')
