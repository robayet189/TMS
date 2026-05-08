from django.db import models
from django.contrib.auth.models import User


class UserProfile(models.Model):
    INSTITUTION_TYPES = [
        ('educational', 'Educational'),
        ('industrial', 'Industrial'),
    ]

    USER_TYPES = [
        ('student', 'Student'),
        ('faculty', 'Faculty'),
        ('staff', 'Staff'),
        ('admin', 'Admin'),
        ('driver', 'Driver'),
        ('executive', 'Executive'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    phone = models.CharField(max_length=15, blank=True)
    institution_type = models.CharField(max_length=50, blank=True)
    user_type = models.CharField(max_length=20, choices=USER_TYPES, default='student')
    institution_id = models.CharField(max_length=50, blank=True)
    department = models.CharField(max_length=100, blank=True)
    is_pass_active = models.BooleanField(default=False)
    pass_valid_until = models.DateField(null=True, blank=True)
    pass_id = models.CharField(max_length=50, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username} - {self.institution_id}"

    class Meta:
        verbose_name = "User Profile"
        verbose_name_plural = "User Profiles"


from django.db import models
from django.contrib.auth.models import User


class Route(models.Model):
    """Bus route information"""
    code = models.CharField(max_length=10, unique=True)  # A1, B3, C2, etc.
    start = models.CharField(max_length=100)
    end = models.CharField(max_length=100)
    distance_km = models.DecimalField(max_digits=5, decimal_places=1, null=True, blank=True)

    def __str__(self):
        return f"{self.code}: {self.start} → {self.end}"


class Bus(models.Model):
    """Bus details"""
    bus_number = models.CharField(max_length=20, unique=True)
    capacity = models.IntegerField(default=40)
    driver_name = models.CharField(max_length=100)
    driver_phone = models.CharField(max_length=15, blank=True)
    has_ac = models.BooleanField(default=False)
    has_wifi = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.bus_number} - {self.driver_name}"


class Schedule(models.Model):
    """Bus schedule for specific dates"""
    route = models.ForeignKey(Route, on_delete=models.CASCADE, related_name='schedules')
    bus = models.ForeignKey(Bus, on_delete=models.CASCADE, related_name='schedules')
    departure_time = models.TimeField()
    arrival_time = models.TimeField(null=True, blank=True)
    travel_date = models.DateField()
    fare = models.DecimalField(max_digits=8, decimal_places=2, default=60.00)
    is_active = models.BooleanField(default=True)
    available_seats = models.IntegerField(default=40)

    class Meta:
        unique_together = ['route', 'travel_date', 'departure_time']
        ordering = ['travel_date', 'departure_time']

    def __str__(self):
        return f"{self.route.code} - {self.departure_time} on {self.travel_date}"
    
   

class Booking(models.Model):
    """Ticket booking information"""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('cancelled', 'Cancelled'),
        ('completed', 'Completed'),
    ]
    
    PAYMENT_STATUS = [
        ('unpaid', 'Unpaid'),
        ('paid', 'Paid'),
        ('refunded', 'Refunded'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='bookings')
    schedule = models.ForeignKey(Schedule, on_delete=models.CASCADE, related_name='bookings')
    booking_date = models.DateTimeField(auto_now_add=True)
    number_of_seats = models.IntegerField(default=1)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='confirmed')
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS, default='paid')
    booking_id = models.CharField(max_length=50, unique=True, blank=True)
    passenger_name = models.CharField(max_length=100, blank=True)
    passenger_phone = models.CharField(max_length=15, blank=True)
    passenger_email = models.CharField(max_length=100, blank=True)
    seat_numbers = models.CharField(max_length=200, blank=True)
    travel_date = models.DateField(null=True, blank=True)
    
    def save(self, *args, **kwargs):
        if not self.booking_id:
            import random
            import string
            self.booking_id = 'TR' + ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
        if not self.travel_date and self.schedule:
            self.travel_date = self.schedule.travel_date
        super().save(*args, **kwargs)
    
    def __str__(self):
        seat_info = f" - Seats: {self.seat_numbers}" if self.seat_numbers else ""
        return f"Booking {self.booking_id} - {self.passenger_name or self.user.username}{seat_info}"
    
    class Meta:
<<<<<<< Updated upstream
        ordering = ['-booking_date']  
=======
        ordering = ['-created_at']


class UserPass(models.Model):
    """User's active passes"""
    PASS_TYPES = [
        ('monthly', 'Monthly Pass'),
        ('semester', 'Semester Pass'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='passes')
    pass_type = models.CharField(max_length=20, choices=PASS_TYPES)
    transaction = models.OneToOneField(PaymentTransaction, on_delete=models.CASCADE, related_name='user_pass')
    
    start_date = models.DateField()
    end_date = models.DateField()
    is_active = models.BooleanField(default=True)
    
    total_rides = models.IntegerField(default=0)
    remaining_rides = models.IntegerField(default=0)  # For limited rides
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.user.username} - {self.pass_type} (Valid until {self.end_date})"
    
    class Meta:
        ordering = ['-created_at']




        # ==================== CHAT MODELS ====================

class ChatRoom(models.Model):
    """Chat room for user-admin or driver-admin conversations"""
    ROOM_TYPES = [
        ('user_admin', 'User-Admin'),
        ('driver_admin', 'Driver-Admin'),
    ]
    
    room_id = models.CharField(max_length=100, unique=True)
    room_type = models.CharField(max_length=20, choices=ROOM_TYPES)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name='chat_rooms')
    admin = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name='admin_chat_rooms')
    created_at = models.DateTimeField(auto_now_add=True)
    last_message = models.TextField(blank=True)
    last_message_time = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        return f"Room: {self.room_id}"
    
    class Meta:
        ordering = ['-last_message_time']


class ChatMessage(models.Model):
    """Individual chat messages"""
    room = models.ForeignKey(ChatRoom, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages')
    receiver = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_messages', null=True, blank=True)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.sender.username}: {self.message[:50]}"
    
    class Meta:
        ordering = ['created_at']


class UserOnlineStatus(models.Model):
    """Track user online status"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='online_status')
    is_online = models.BooleanField(default=False)
    last_seen = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.user.username} - {'Online' if self.is_online else 'Offline'}"
>>>>>>> Stashed changes
