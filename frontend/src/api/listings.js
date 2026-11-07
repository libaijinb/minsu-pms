import request from './request'

// 房源/日历/价格规则
export const listListings = (params) => request.get('/listings/', { params })
export const getListing = (id) => request.get(`/listings/${id}/`)
export const createListing = (data) => request.post('/listings/', data)
export const updateListing = (id, data) => request.patch(`/listings/${id}/`, data)
export const submitListing = (id) => request.post(`/listings/${id}/submit/`)           // 提交审核
export const auditListing = (id, passed, reason) => request.post(`/listings/${id}/audit/`, { passed, reason })
export const onlineListing = (id) => request.post(`/listings/${id}/online/`)
export const offlineListing = (id) => request.post(`/listings/${id}/offline/`)
export const getCalendar = (id, params) => request.get(`/listings/${id}/calendar/`, { params })
export const batchPrice = (id, data) => request.post(`/listings/${id}/batch-price/`, data)     // 批量改价
export const closeDates = (id, dates, reason) => request.post(`/listings/${id}/close-dates/`, { dates, reason })
export const openDates = (id, dates) => request.post(`/listings/${id}/open-dates/`, { dates })
export const listPriceRules = (params) => request.get('/price-rules/', { params })
export const createPriceRule = (data) => request.post('/price-rules/', data)
export const updatePriceRule = (id, data) => request.patch(`/price-rules/${id}/`, data)
export const deletePriceRule = (id) => request.delete(`/price-rules/${id}/`)
