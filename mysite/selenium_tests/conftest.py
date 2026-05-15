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

# ✅ STEP 2: Initialize Django app registry (only once, at module level)
import django
django.setup()

# ✅ STEP 3: Now it's safe to import Django models (for reference only, not for DB access in fixtures)
from django.contrib.auth.models import User
from myapp.models import UserProfile, Route, Bus, Schedule
from django.utils import timezone
from datetime import datetime

# =========================================================================
# WebDriver Fixture (Function Scope for Isolation)
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
# ✅ REMOVED: seed_dev_database fixture (causes DB access error in Selenium tests)
# Instead, seed your dev database manually using the script below
# =========================================================================

@pytest.fixture
def wait(driver):
    return WebDriverWait(driver, 10)