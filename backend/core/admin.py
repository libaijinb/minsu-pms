from django.contrib import admin

from .models import Notification, Review


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ['id', 'listing', 'type', 'rating', 'reviewer', 'reviewee', 'created_at']
    list_filter = ['type', 'rating']
    search_fields = ['listing__title', 'reviewer__username']


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'event', 'title', 'is_read', 'created_at']
    list_filter = ['is_read', 'event']
    search_fields = ['user__username', 'title']
