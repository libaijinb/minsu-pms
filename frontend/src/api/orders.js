import request from './request'

// 订单全链路
export const createOrder = (data) => request.post('/orders/', data)
export const listOrders = (params) => request.get('/orders/', { params })
export const getOrder = (orderNo) => request.get(`/orders/${orderNo}/`)
export const payOrder = (orderNo) => request.post(`/orders/${orderNo}/pay/`)
export const confirmOrder = (orderNo) => request.post(`/orders/${orderNo}/confirm/`)
export const cancelOrder = (orderNo, reason) => request.post(`/orders/${orderNo}/cancel/`, { reason })
export const checkinOrder = (orderNo, data) => request.post(`/orders/${orderNo}/checkin/`, data)
export const checkoutOrder = (orderNo) => request.post(`/orders/${orderNo}/checkout/`)
export const noshowOrder = (orderNo) => request.post(`/orders/${orderNo}/noshow/`)

// 查房（运营）
export const listInspections = (params) => request.get('/inspections/', { params })
export const submitInspection = (data) => request.post('/inspections/submit/', data)
