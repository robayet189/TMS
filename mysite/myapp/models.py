from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

class UserProfile(models.Model):
    USER_TYPES = [
        ('student', 'Student'),
        ('faculty', 'Faculty'),
        ('staff', 'Staff'),
        ('admin', 'Admin'),
        ('driver', 'Driver'),
    ]
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    phone = models.CharField(max_length=15, blank=True)
    user_type = models.CharField(max_length=20, choices=USER_TYPES, default='student')
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
    STATUS_CHOICES = [('pending', 'Pending'), ('confirmed', 'Confirmed'), ('cancelled', 'Cancelled'), ('completed', 'Completed')]
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

    def save(self, *args, **kwargs):
        if not self.booking_id:
            import random, string
            self.booking_id = 'BK-' + ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        super().save(*args, **kwargs)

    def __str__(self):
        return self.booking_id