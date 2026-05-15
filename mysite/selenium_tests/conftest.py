import os
import sys

# ✅ STEP 1: Set Django settings BEFORE importing anything Django-related
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mysite.settings')

# ✅ STEP 2: Initialize Django app registry
import django
django.setup()

import pytest
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager

# ✅ STEP 3: Now it's safe to import Django models
from django.contrib.auth.models import User
from myapp.models import UserProfile, Route, Bus, Schedule
from django.utils import timezone
from datetime import datetime

# =========================================================================
# WebDriver Fixture (Function Scope)
# =========================================================================
@pytest.fixture(scope="function")
def driver():
    """Initialize Chrome WebDriver with anti-bot settings"""
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
    driver.implicitly_wait(8)
    yield driver
    driver.quit()

@pytest.fixture(scope="session")
def base_url():
    return os.getenv("BASE_URL", "http://127.0.0.1:8000")

@pytest.fixture(scope="session")
def test_admin_credentials():
    return {"username": "admin@test.com", "password": "AdminPass123!"}

@pytest.fixture(scope="session")
def test_driver_credentials():
    return {"username": "driver@test.com", "password": "DriverPass123!"}

@pytest.fixture(scope="session")
def test_user_credentials():
    return {"username": "student@test.com", "password": "TestPass123!"}

# =========================================================================
# ✅ Direct Dev DB Seeding (Bypasses pytest-django's test DB isolation)
# =========================================================================
@pytest.fixture(scope="session", autouse=True)
def seed_dev_database():
    """Seed the main development database so Selenium tests have data"""
    from django.test.utils import setup_test_environment
    setup_test_environment()
    
    # Admin
    admin, _ = User.objects.get_or_create(
        username="admin", 
        defaults={"email": "admin@test.com", "is_active": True, "is_staff": True}
    )
    admin.set_password("AdminPass123!")
    admin.save()
    UserProfile.objects.get_or_create(
        user=admin, 
        defaults={"user_type": "admin", "phone": "01700000001", "institution_type": "university"}
    )

    # Driver
    driver_user, _ = User.objects.get_or_create(
        username="driver", 
        defaults={"email": "driver@test.com", "is_active": True}
    )
    driver_user.set_password("DriverPass123!")
    driver_user.save()
    UserProfile.objects.get_or_create(
        user=driver_user, 
        defaults={"user_type": "driver", "phone": "01700000002", "institution_type": "university"}
    )

    # Student
    student, _ = User.objects.get_or_create(
        username="student", 
        defaults={"email": "student@test.com", "is_active": True}
    )
    student.set_password("TestPass123!")
    student.save()
    UserProfile.objects.get_or_create(
        user=student, 
        defaults={"user_type": "student", "phone": "01700000003", "institution_type": "university", "institution_id": "STU001"}
    )

    # Route & Bus & Schedule (for booking tests)
    route, _ = Route.objects.get_or_create(
        code="R1", 
        defaults={"start": "Main Gate", "end": "Academic Building", "distance_km": 5.5}
    )
    bus, _ = Bus.objects.get_or_create(
        bus_number="BUS-01", 
        defaults={"capacity": 40, "has_ac": True}
    )
    today = timezone.now().date()
    Schedule.objects.get_or_create(
        route=route, 
        bus=bus, 
        travel_date=today,
        departure_time=datetime.strptime("08:00", "%H:%M").time(),
        defaults={"fare": 40, "available_seats": 35}
    )

@pytest.fixture
def wait(driver):
    return WebDriverWait(driver, 10)