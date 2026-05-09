from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

class UserProfile(models.Model):
    USER_TYPES = [
        ('student', 'Student'),
        ('faculty', 'Faculty'),
        ('staff', 'Staff'),
        ('admin', 'Admin'),
        ('driver', 'Driver'),  # ✅ Already exists - Driver user type
    ]
    INSTITUTION_TYPES = [
        ('educational', 'Educational'),
        ('industrial', 'Industrial'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    phone = models.CharField(max_length=15, blank=True)
    user_type = models.CharField(max_length=20, choices=USER_TYPES, default='student')
    institution_type = models.CharField(max_length=50, blank=True, null=True)
    institution_id = models.CharField(max_length=50, blank=True)
    department = models.CharField(max_length=100, blank=True)
    is_pass_active = models.BooleanField(default=False)
    pass_valid_until = models.DateField(null=True, blank=True)
    pass_id = models.CharField(max_length=50, blank=True)

    def __str__(self):
        return f"{self.user.username} ({self.user_type})"

class Bus(models.Model):
    bus_number = models.CharField(max_length=20, unique=True)
    capacity = models.IntegerField(default=40)
    driver_name = models.CharField(max_length=100)
    driver_phone = models.CharField(max_length=15, blank=True)
    has_ac = models.BooleanField(default=False)
    has_wifi = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.bus_number

class Route(models.Model):
    code = models.CharField(max_length=10, unique=True)
    start = models.CharField(max_length=100)
    end = models.CharField(max_length=100)
    distance_km = models.DecimalField(max_digits=5, decimal_places=1, null=True, blank=True)

    def __str__(self):
        return f"{self.code}: {self.start} → {self.end}"

class Schedule(models.Model):
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

    def __str__(self):
        return f"{self.route.code} on {self.travel_date}"

class Booking(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending Approval'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('cancelled', 'Cancelled'),
        ('completed', 'Completed'),
    ]
    PAYMENT_CHOICES = [('bkash', 'bKash'), ('sslcommerz', 'SSLCommerz'), ('cash', 'Cash')]

    booking_id = models.CharField(max_length=20, unique=True, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='bookings')
    schedule = models.ForeignKey(Schedule, on_delete=models.CASCADE, related_name='bookings')
    seat_number = models.CharField(max_length=10)
    booking_date = models.DateTimeField(auto_now_add=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    passenger_name = models.CharField(max_length=100)
    admin_remarks = models.TextField(blank=True, null=True, help_text="Admin approval/rejection remarks")
    approved_at = models.DateTimeField(null=True, blank=True)
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_bookings')

    def save(self, *args, **kwargs):
        if not self.booking_id:
            import random, string
            self.booking_id = 'BK-' + ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.booking_id} - {self.passenger_name}"


class BusLocation(models.Model):
    """Track bus locations"""
    bus = models.ForeignKey(Bus, on_delete=models.CASCADE, related_name='locations')
    latitude = models.FloatField()
    longitude = models.FloatField()
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-updated_at']
    
    def __str__(self):
        return f"{self.bus.bus_number} - {self.latitude}, {self.longitude}"


# ==================== PAYMENT MODELS ====================

class PaymentMethod(models.Model):
    """Available payment methods"""
    name = models.CharField(max_length=50)
    code = models.CharField(max_length=20, unique=True)
    is_active = models.BooleanField(default=True)
    icon = models.CharField(max_length=50, blank=True)
    
    def __str__(self):
        return self.name


class PaymentTransaction(models.Model):
    """All payment transactions"""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
    ]
    
    PAYMENT_TYPE_CHOICES = [
        ('pass', 'Transport Pass'),
        ('single', 'Single Trip'),
        ('booking', 'Booking Payment'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='payments')
    booking = models.ForeignKey('Booking', on_delete=models.SET_NULL, null=True, blank=True, related_name='payments')
    
    transaction_id = models.CharField(max_length=100, unique=True, blank=True)
    payment_method = models.CharField(max_length=50)
    payment_type = models.CharField(max_length=20, choices=PAYMENT_TYPE_CHOICES, default='pass')
    
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    pass_type = models.CharField(max_length=20, blank=True)
    pass_valid_from = models.DateField(null=True, blank=True)
    pass_valid_until = models.DateField(null=True, blank=True)
    
    payment_details = models.JSONField(default=dict, blank=True)
    remarks = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def save(self, *args, **kwargs):
        if not self.transaction_id:
            import random
            import string
            self.transaction_id = 'TXN' + ''.join(random.choices(string.ascii_uppercase + string.digits, k=12))
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.transaction_id} - {self.user.username} - ৳{self.amount}"
    
    class Meta:
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
    remaining_rides = models.IntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.user.username} - {self.pass_type} (Valid until {self.end_date})"
    
    class Meta:
        ordering = ['-created_at']


# ==================== CHAT SYSTEM MODELS ====================

class ChatRoom(models.Model):
    """Chat room for user-admin communication"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='chat_rooms', null=True, blank=True)
    admin = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='admin_chat_rooms')
    booking = models.ForeignKey('Booking', on_delete=models.SET_NULL, null=True, blank=True, related_name='chat_rooms')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return f"Chat: {self.user.username} - {self.created_at.strftime('%Y-%m-%d %H:%M')}"
    
    class Meta:
        ordering = ['-updated_at']


class ChatMessage(models.Model):
    """Individual chat messages"""
    MESSAGE_TYPES = [
        ('text', 'Text'),
        ('image', 'Image'),
        ('file', 'File'),
    ]
    
    room = models.ForeignKey(ChatRoom, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages')
    message = models.TextField()
    message_type = models.CharField(max_length=20, choices=MESSAGE_TYPES, default='text')
    attachment = models.FileField(upload_to='chat_attachments/', null=True, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.sender.username}: {self.message[:50]}"
    
    class Meta:
        ordering = ['created_at']


# ==================== DRIVER MODULE MODELS (NEW - For driver_dashboard.html) ====================
# ✅ ADDED: Driver model for driver-specific data
class Driver(models.Model):
    """Driver profile extending UserProfile"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='driver_profile')
    license_number = models.CharField(max_length=50, unique=True)
    license_expiry = models.DateField()
    phone = models.CharField(max_length=15)
    address = models.TextField()
    emergency_contact = models.CharField(max_length=15)
    is_approved = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    assigned_bus = models.ForeignKey(Bus, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_drivers')
    assigned_route = models.ForeignKey(Route, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_drivers')
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.user.get_full_name()} - {self.license_number}"


# ✅ ADDED: Trip model for driver trip management
class Trip(models.Model):
    """Trip assignment for drivers"""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('ongoing', 'Ongoing'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]
    
    driver = models.ForeignKey(Driver, on_delete=models.CASCADE, related_name='trips')
    route = models.ForeignKey(Route, on_delete=models.CASCADE)
    bus = models.ForeignKey(Bus, on_delete=models.CASCADE)
    travel_date = models.DateField()
    departure_time = models.TimeField()
    arrival_time = models.TimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    current_lat = models.FloatField(null=True, blank=True)
    current_lng = models.FloatField(null=True, blank=True)
    last_location_update = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.route.code} - {self.travel_date} ({self.driver.user.get_full_name()})"


# ✅ ADDED: TripStop model for route stops
class TripStop(models.Model):
    """Individual stops in a trip"""
    trip = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name='stops')
    stop_name = models.CharField(max_length=200)
    stop_order = models.IntegerField()
    scheduled_time = models.TimeField()
    arrival_time = models.TimeField(null=True, blank=True)
    departure_time = models.TimeField(null=True, blank=True)
    is_completed = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['stop_order']
    
    def __str__(self):
        return f"{self.trip.route.code} - {self.stop_name} (Order {self.stop_order})"


# ✅ ADDED: VehicleIssue model for driver issue reporting
class VehicleIssue(models.Model):
    """Vehicle issue reporting by drivers"""
    SEVERITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    ]
    
    driver = models.ForeignKey(Driver, on_delete=models.CASCADE)
    bus = models.ForeignKey(Bus, on_delete=models.CASCADE)
    issue_description = models.TextField()
    severity = models.CharField(max_length=20, choices=SEVERITY_CHOICES, default='medium')
    reported_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    is_resolved = models.BooleanField(default=False)
    
    def __str__(self):
        return f"Issue by {self.driver.user.get_full_name()} - {self.reported_at}"