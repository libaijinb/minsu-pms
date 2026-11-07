from django.contrib import admin

from .models import (BookingOrder, CheckinRecord, DepositDeduction,
                     InspectionRecord, OrderStatusLog, PaymentRecord)


@admin.register(BookingOrder)
class BookingOrderAdmin(admin.ModelAdmin):
    list_display = ['order_no', 'listing', 'guest', 'checkin_date', 'checkout_date',
                    'nights', 'total_amount', 'status', 'channel', 'created_at']
    list_filter = ['status', 'channel']
    search_fields = ['order_no', 'listing__title', 'guest__username']
    date_hierarchy = 'created_at'


@admin.register(OrderStatusLog)
class OrderStatusLogAdmin(admin.ModelAdmin):
    list_display = ['id', 'order', 'from_status', 'to_status', 'operator', 'created_at']
    list_filter = ['to_status']
    search_fields = ['order__order_no']


@admin.register(PaymentRecord)
class PaymentRecordAdmin(admin.ModelAdmin):
    list_display = ['id', 'order', 'amount', 'channel', 'trade_no', 'status', 'paid_at']
    list_filter = ['status', 'channel']
    search_fields = ['trade_no', 'order__order_no']


@admin.register(CheckinRecord)
class CheckinRecordAdmin(admin.ModelAdmin):
    list_display = ['id', 'order', 'id_card', 'phone', 'deposit_amount', 'deposit_status',
                    'actual_checkin_at', 'actual_checkout_at']
    list_filter = ['deposit_status']


@admin.register(InspectionRecord)
class InspectionRecordAdmin(admin.ModelAdmin):
    list_display = ['id', 'order', 'damage_total', 'conclusion', 'inspector', 'created_at']
    list_filter = ['conclusion']


@admin.register(DepositDeduction)
class DepositDeductionAdmin(admin.ModelAdmin):
    list_display = ['id', 'inspection', 'item', 'amount', 'repair_ticket', 'status']
    list_filter = ['status']
