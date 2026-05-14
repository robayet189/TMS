"""
Pytest configuration and fixtures for Easy Transport Selenium tests.
"""

import os
import pytest

# ========================================================================
# DJANGO SETTINGS - Let pytest-django handle initialization
# ========================================================================
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mysite.settings')

# ========================================================================
# IMPORT SELENIUM ONLY - NO DJANGO MODELS AT MODULE LEVEL
# ========================================================================
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager


@pytest.fixture(scope="function")
def driver():
    """Chrome WebDriver setup"""
    chrome_options = Options()
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    
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


# ========================================================================
# ✅ CRITICAL: seed_test_data - NO DJANGO IMPORTS AT MODULE LEVEL
# All Django imports happen INSIDE this function only
# ========================================================================
@pytest.fixture(autouse=True)
def seed_test_data(db):
    """
    Seed database with test data before each test.
    
    IMPORTANT: All Django model imports happen INSIDE this function,
    NOT at module level. This ensures Django is fully initialized.
    """
    # ✅ Import Django models HERE ONLY - inside the function
    from django.contrib.auth.models import User
    from myapp.models import UserProfile, Route, Bus, Schedule
    from django.utils import timezone
    from datetime import datetime, timedelta
    
    # Create test student user
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
        defaults={"capacity": 40, "has_ac": True, "is_active": True}
    )
    
    # Create schedule for TODAY
    today = timezone.now().date()
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