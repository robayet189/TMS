from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from .models import UserProfile, Bus, Route, Schedule, Booking

class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'Profile Info'

class CustomUserAdmin(BaseUserAdmin):
    inlines = (UserProfileInline,)
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'get_user_type')
    def get_user_type(self, obj):
        return obj.profile.user_type if hasattr(obj, 'profile') else 'N/A'
    get_user_type.short_description = 'User Type'

admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'user_type', 'institution_id', 'department', 'is_pass_active')
    list_filter = ('user_type', 'is_pass_active')
    search_fields = ('user__username', 'user__email', 'institution_id')

@admin.register(Bus)
class BusAdmin(admin.ModelAdmin):
    list_display = ('bus_number', 'driver_name', 'capacity', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('bus_number', 'driver_name')

@admin.register(Route)
class RouteAdmin(admin.ModelAdmin):
    list_display = ('code', 'start', 'end')
    search_fields = ('code', 'start', 'end')

@admin.register(Schedule)
class ScheduleAdmin(admin.ModelAdmin):
    list_display = ('route', 'bus', 'travel_date', 'departure_time', 'fare', 'available_seats')
    list_filter = ('is_active', 'travel_date')
    search_fields = ('route__code', 'bus__bus_number')

@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ('booking_id', 'user', 'schedule', 'amount', 'status', 'payment_method')
    list_filter = ('status', 'payment_method')
    search_fields = ('booking_id', 'user__username', 'passenger_name')