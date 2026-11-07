from django.contrib import admin

from .models import Calendar, Listing, PriceRule


@admin.register(Listing)
class ListingAdmin(admin.ModelAdmin):
    list_display = ['id', 'title', 'owner', 'type', 'city', 'status', 'rating', 'rating_count', 'created_at']
    list_filter = ['status', 'type', 'city']
    search_fields = ['title', 'owner__username', 'address']


@admin.register(Calendar)
class CalendarAdmin(admin.ModelAdmin):
    list_display = ['id', 'listing', 'date', 'status', 'price']
    list_filter = ['status', 'date']
    search_fields = ['listing__title']


@admin.register(PriceRule)
class PriceRuleAdmin(admin.ModelAdmin):
    list_display = ['id', 'listing', 'type', 'price', 'date', 'start_date', 'end_date', 'min_nights', 'discount_rate']
    list_filter = ['type']
