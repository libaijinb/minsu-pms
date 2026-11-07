from django.contrib import admin

from .models import PayoutRecord, Settlement


@admin.register(Settlement)
class SettlementAdmin(admin.ModelAdmin):
    list_display = ['id', 'landlord', 'period', 'order_count', 'gross', 'commission',
                    'service_cost', 'damage', 'net_amount', 'status', 'created_at']
    list_filter = ['status', 'period']
    search_fields = ['landlord__username']


@admin.register(PayoutRecord)
class PayoutRecordAdmin(admin.ModelAdmin):
    list_display = ['id', 'settlement', 'amount', 'status', 'trade_no', 'retry_count', 'created_at']
    list_filter = ['status']
    search_fields = ['trade_no']
