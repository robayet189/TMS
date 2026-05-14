"""
Pytest configuration and fixtures for Easy Transport Selenium tests.
Provides WebDriver setup, base URL, test credentials, and test data seeding.
"""

import os
import sys
import pytest

# ✅ CRITICAL: Configure Django BEFORE importing Django models
# This must be at the TOP of the file, before any Django imports
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mysite.settings')

# Now import Django and setup
import django
django.setup()  # ✅ Initialize Django

# Now it's safe to import Django models
from django.contrib.auth.models import User
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
from myapp.models import UserProfile, Route, Bus, Schedule, Booking
from django.utils import timezone
from datetime import datetime, timedelta


@pytest.fixture(scope="function")
def driver():
    """
    Chrome WebDriver setup with optimized options for testing.
    Yields driver instance and ensures cleanup after each test.
    """
    chrome_options = Options()
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option("useAutomationExtension", False)
    
    # Enable browser console logging for debugging
    chrome_options.set_capability('goog:loggingPrefs', {'browser': 'ALL', 'performance': 'ALL'})
    
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    
    # Set implicit wait for element finding
    driver.implicitly_wait(10)
    
    # Execute CDP command to bypass automation detection
    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": """
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            })
        """
    })
    
    yield driver
    
    # Cleanup: quit driver after test
    driver.quit()


@pytest.fixture(scope="session")
def base_url():
    """
    Returns the base URL for the application.
    Used by page objects to construct full URLs.
    """
    return os.getenv("BASE_URL", "http://127.0.0.1:8000")


@pytest.fixture(scope="session")
def test_admin_credentials():
    """
    Returns admin test credentials.
    Use in tests requiring admin authentication.
    """
    return {
        "username": "admin@test.com",
        "password": "AdminPass123!",
        "user_type": "admin"
    }


@pytest.fixture(scope="session")
def test_driver_credentials():
    """
    Returns driver test credentials.
    Use in tests requiring driver authentication.
    """
    return {
        "username": "driver@test.com",
        "password": "DriverPass123!",
        "user_type": "driver"
    }


@pytest.fixture(scope="session")
def test_user_credentials():
    """
    Returns student/user test credentials.
    Use in tests requiring regular user authentication.
    """
    return {
        "username": "student@test.com",
        "password": "TestPass123!",
        "user_type": "student"
    }


@pytest.fixture(autouse=True, scope="session")
def seed_test_data(db):
    """
    Auto-run fixture to seed database with test data before tests.
    Creates users, routes, buses, and schedules for booking tests.
    """
    # Create test admin user
    admin_user, _ = User.objects.get_or_create(
        username="admin",
        defaults={"email": "admin@test.com", "is_active": True, "is_staff": True}
    )
    admin_user.set_password("AdminPass123!")
    admin_user.save()
    UserProfile.objects.get_or_create(
        user=admin_user,
        defaults={"user_type": "admin", "phone": "01700000001", "institution_type": "university"}
    )
    
    # Create test driver user
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
    
    # Create test student user
    student_user, _ = User.objects.get_or_create(
        username="student",
        defaults={"email": "student@test.com", "is_active": True}
    )
    student_user.set_password("TestPass123!")
    student_user.save()
    UserProfile.objects.get_or_create(
        user=student_user,
        defaults={"user_type": "student", "phone": "01700000003", "institution_type": "university", "institution_id": "STU001"}
    )
    
    # Create test route
    route, _ = Route.objects.get_or_create(
        code="R1",
        defaults={
            "start": "Main Gate",
            "end": "Academic Building",
            "distance_km": 5.5,
            "is_active": True
        }
    )
    
    # Create test bus
    bus, _ = Bus.objects.get_or_create(
        bus_number="BUS-01",
        defaults={
            "capacity": 40,
            "has_ac": True,
            "is_active": True
        }
    )
    
    # Create schedule for TODAY (critical for booking tests)
    today = timezone.now().date()
    schedule, _ = Schedule.objects.get_or_create(
        route=route,
        bus=bus,
        travel_date=today,
        departure_time=datetime.strptime("08:00", "%H:%M").time(),
        defaults={
            "fare": 40,
            "available_seats": 35,
            "is_active": True
        }
    )
    
    return {
        "admin_user": admin_user,
        "driver_user": driver_user,
        "student_user": student_user,
        "route": route,
        "bus": bus,
        "schedule": schedule
    }


@pytest.fixture
def wait(driver):
    """
    Returns a WebDriverWait instance with default timeout.
    Use for explicit waits in tests.
    """
    return WebDriverWait(driver, 10)


def save_screenshot(driver, name):
    """
    Helper function to save screenshot for debugging.
    Saves to screenshots/ directory.
    """
    os.makedirs("screenshots", exist_ok=True)
    filepath = f"screenshots/{name}.png"
    driver.save_screenshot(filepath)
    print(f"Screenshot saved: {filepath}")
    return filepath