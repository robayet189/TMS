from django.contrib import admin
from .models import UserProfile

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'phone', 'institution_type', 'user_type', 'institution_id', 'created_at']
    list_filter = ['institution_type', 'user_type']
    search_fields = ['user__username', 'user__email', 'phone', 'institution_id']