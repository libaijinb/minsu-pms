import request from './request'

// 结算分账
export const listSettlements = (params) => request.get('/settlements/', { params })
export const getSettlement = (id) => request.get(`/settlements/${id}/`)
export const payoutSettlement = (id, success = true) => request.post(`/settlements/${id}/payout/?success=${success}`)
export const runSettlement = (data) => request.post('/settlements/run/', data)
export const retryPayout = (id) => request.post(`/payouts/${id}/retry/`)
