#!/usr/bin/env python
"""
Seed script for Easy Transport development database.
Run this BEFORE running Selenium tests to ensure test users and data exist.
"""
import os
import sys

# ✅ FIX: Use raw string (r""") for docstring to handle Windows backslashes safely
DESCRIPTION = r"""
Usage:
    cd C:\Users\masfi\OneDrive\Desktop\Easy-Transport\mysite
    python selenium_tests/seed_dev_db.py
"""

# ✅ STEP 1: Add project root to Python path
# The script is inside 'selenium_tests', so we go up one level to 'mysite' (project root)
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# ✅ STEP 2: Set Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mysite.settings')

# ✅ STEP 3: Initialize Django
import django
try:
    django.setup()
except Exception as e:
    print(f"❌ Error setting up Django: {e}")
    print("Make sure you have run 'python manage.py migrate' first.")
    sys.exit(1)

# ✅ STEP 4: Now import Django models
from django.contrib.auth.models import User
from myapp.models import UserProfile, Route, Bus, Schedule
from django.utils import timezone
from datetime import datetime

def seed_database():
    """Seed development database with test data"""
    print("🌱 Seeding development database...")
    
    try:
        # Admin user
        admin, created = User.objects.get_or_create(
            username="admin",
            defaults={"email": "admin@test.com", "is_active": True, "is_staff": True}
        )
        if created:
            admin.set_password("AdminPass123!")
            admin.save()
            print("✅ Admin user created")
        UserProfile.objects.get_or_create(
            user=admin,
            defaults={"user_type": "admin", "phone": "01700000001", "institution_type": "university"}
        )

        # Driver user
        driver_user, created = User.objects.get_or_create(
            username="driver",
            defaults={"email": "driver@test.com", "is_active": True}
        )
        if created:
            driver_user.set_password("DriverPass123!")
            driver_user.save()
            print("✅ Driver user created")
        UserProfile.objects.get_or_create(
            user=driver_user,
            defaults={"user_type": "driver", "phone": "01700000002", "institution_type": "university"}
        )

        # Student user
        student, created = User.objects.get_or_create(
            username="student",
            defaults={"email": "student@test.com", "is_active": True}
        )
        if created:
            student.set_password("TestPass123!")
            student.save()
            print("✅ Student user created")
        UserProfile.objects.get_or_create(
            user=student,
            defaults={"user_type": "student", "phone": "01700000003", "institution_type": "university", "institution_id": "STU001"}
        )

        # Route, Bus, Schedule for booking tests
        route, _ = Route.objects.get_or_create(
            code="R1",
            defaults={"start": "Main Gate", "end": "Academic Building", "distance_km": 5.5}
        )
        bus, _ = Bus.objects.get_or_create(
            bus_number="BUS-01",
            defaults={"capacity": 40, "has_ac": True}
        )
        today = timezone.now().date()
        schedule, created = Schedule.objects.get_or_create(
            route=route,
            bus=bus,
            travel_date=today,
            departure_time=datetime.strptime("08:00", "%H:%M").time(),
            defaults={"fare": 40, "available_seats": 35}
        )
        if created:
            print("✅ Route, Bus, and Schedule created for testing")
        
        print("🎉 Database seeding complete!")
        
    except Exception as e:
        print(f"❌ Error seeding database: {e}")

if __name__ == "__main__":
    print(DESCRIPTION.strip())
    seed_database()