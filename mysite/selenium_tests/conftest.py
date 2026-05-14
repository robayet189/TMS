"""
Pytest configuration for Easy Transport Selenium tests.
MINIMAL VERSION - No Django imports at module level.
"""

import os
import pytest

# Set Django settings BEFORE any imports
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mysite.settings')

# Import ONLY Selenium (NO Django models here!)
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager


@pytest.fixture(scope="function")
def driver():
    """Chrome WebDriver setup"""
    chrome_options = Options()
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--disable-gpu")
    
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    driver.implicitly_wait(10)
    yield driver
    driver.quit()


@pytest.fixture(scope="session")
def base_url():
    return os.getenv("BASE_URL", "http://127.0.0.1:8000")


@pytest.fixture(scope="session")
def test_user_credentials():
    return {
        "username": "student@test.com",
        "password": "TestPass123!",
        "user_type": "student"
    }


# ✅ FIXED: seed_test_data - Django imports INSIDE function ONLY
@pytest.fixture
def seed_test_data(db):
    """Seed database - Django imports happen HERE, not at module level"""
    # Import Django models INSIDE the function
    from django.contrib.auth.models import User
    from myapp.models import UserProfile, Route, Bus, Schedule
    from django.utils import timezone
    from datetime import datetime, timedelta
    
    today = timezone.now().date()
    
    student_user, _ = User.objects.get_or_create(
        username="student",
        defaults={"email": "student@test.com", "is_active": True}
    )
    student_user.set_password("TestPass123!")
    student_user.save()
    
    UserProfile.objects.get_or_create(
        user=student_user,
        defaults={
            "user_type": "student",
            "phone": "01700000003",
            "institution_type": "university",
            "institution_id": "STU001"
        }
    )
    
    route, _ = Route.objects.get_or_create(
        code="R1",
        defaults={
            "start": "Main Gate",
            "end": "Academic Building",
            "distance_km": 5.5,
            "is_active": True
        }
    )
    
    bus, _ = Bus.objects.get_or_create(
        bus_number="BUS-01",
        defaults={"capacity": 40, "has_ac": True, "is_active": True}
    )
    
    Schedule.objects.get_or_create(
        route=route,
        bus=bus,
        travel_date=today,
        departure_time=datetime.strptime("08:00", "%H:%M").time(),
        defaults={"fare": 40, "available_seats": 35, "is_active": True}
    )
    
    return {"student_user": student_user, "route": route, "bus": bus}


@pytest.fixture
def wait(driver):
    return WebDriverWait(driver, 10)