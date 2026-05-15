import os
import sys
import pytest
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager

# ✅ STEP 1: Set Django settings BEFORE importing anything Django-related
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mysite.settings')

# ✅ STEP 2: Initialize Django app registry
import django
django.setup()

# ✅ STEP 3: Now import Django models
from django.contrib.auth.models import User
from myapp.models import UserProfile, Route, Bus, Schedule
from django.utils import timezone
from datetime import datetime

# =========================================================================
# WebDriver Fixture
# =========================================================================
@pytest.fixture(scope="function")
def driver():
    chrome_options = Options()
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option("useAutomationExtension", False)
    
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    driver.implicitly_wait(10)
    driver.maximize_window()
    yield driver
    driver.quit()

@pytest.fixture(scope="session")
def base_url():
    return os.getenv("BASE_URL", "http://127.0.0.1:8000")

# =========================================================================
# ✅ FIXED: Database Seeding with CORRECT user_type values
# =========================================================================
@pytest.fixture(scope="session", autouse=True)
def seed_dev_database():
    """Seed development database with CORRECT user_type for role-based redirects"""
    print("🌱 Seeding development database with role-based users...")
    
    # Admin user - MUST have user_type='admin' for redirect to work
    admin, created = User.objects.get_or_create(
        username="admin",
        defaults={"email": "admin@test.com", "is_active": True, "is_staff": True}
    )
    if created:
        admin.set_password("AdminPass123!")
        admin.save()
        print("✅ Admin user created")
    
    # ✅ CRITICAL: Set user_type='admin' in UserProfile
    admin_profile, _ = UserProfile.objects.get_or_create(user=admin)
    admin_profile.user_type = 'admin'
    admin_profile.phone = "01700000001"
    admin_profile.institution_type = "university"
    admin_profile.save()
    print("✅ Admin profile with user_type='admin' saved")

    # Driver user - MUST have user_type='driver'
    driver_user, created = User.objects.get_or_create(
        username="driver",
        defaults={"email": "driver@test.com", "is_active": True}
    )
    if created:
        driver_user.set_password("DriverPass123!")
        driver_user.save()
        print("✅ Driver user created")
    
    driver_profile, _ = UserProfile.objects.get_or_create(user=driver_user)
    driver_profile.user_type = 'driver'
    driver_profile.phone = "01700000002"
    driver_profile.institution_type = "university"
    driver_profile.save()
    print("✅ Driver profile with user_type='driver' saved")

    # Student user - user_type='student' (default)
    student, created = User.objects.get_or_create(
        username="student",
        defaults={"email": "student@test.com", "is_active": True}
    )
    if created:
        student.set_password("TestPass123!")
        student.save()
        print("✅ Student user created")
    
    student_profile, _ = UserProfile.objects.get_or_create(user=student)
    student_profile.user_type = 'student'
    student_profile.phone = "01700000003"
    student_profile.institution_type = "university"
    student_profile.institution_id = "STU001"
    student_profile.save()
    print("✅ Student profile with user_type='student' saved")

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
    
    print("🎉 Database seeding complete! All users have correct user_type for role-based redirects.")

@pytest.fixture
def wait(driver):
    return WebDriverWait(driver, 15)  # Increased timeout for slower pages