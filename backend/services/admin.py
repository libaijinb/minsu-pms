from django.contrib import admin

from .models import CleaningTask, RepairTicket


@admin.register(CleaningTask)
class CleaningTaskAdmin(admin.ModelAdmin):
    list_display = ['id', 'listing', 'order', 'cleaner', 'task_date', 'slot', 'status', 'created_at']
    list_filter = ['status', 'slot', 'task_date']
    search_fields = ['listing__title', 'cleaner__username']


@admin.register(RepairTicket)
class RepairTicketAdmin(admin.ModelAdmin):
    list_display = ['id', 'listing', 'source', 'title', 'urgency', 'repairer', 'status', 'cost', 'created_at']
    list_filter = ['status', 'source', 'urgency']
    search_fields = ['title', 'listing__title']
