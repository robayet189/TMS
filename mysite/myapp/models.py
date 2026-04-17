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
    phone = models.CharField(max_length=15)
    institution_type = models.CharField(max_length=20, choices=INSTITUTION_TYPES)
    user_type = models.CharField(max_length=20, choices=USER_TYPES)
    institution_id = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username} - {self.institution_id}"

    class Meta:
        verbose_name = "User Profile"
        verbose_name_plural = "User Profiles"