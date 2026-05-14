# selenium_tests/conftest.py
import pytest
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

@pytest.fixture(scope="function")
def driver():
    """Chrome WebDriver Setup"""
    chrome_options = Options()
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--disable-gpu")
    
    chrome_options.set_capability('goog:loggingPrefs', {'browser': 'ALL'})
    
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    driver.implicitly_wait(10)
    
    yield driver
    driver.quit()

@pytest.fixture(scope="session")
def base_url():
    """✅ FIXED: Always return full URL"""
    return "http://127.0.0.1:8000"

@pytest.fixture(scope="session")
def test_admin_credentials():
    return {"username": "admin@test.com", "password": "AdminPass123!"}

@pytest.fixture(scope="session")
def test_driver_credentials():
    return {"username": "driver@test.com", "password": "DriverPass123!"}

@pytest.fixture(scope="session")
def test_user_credentials():
    return {"username": "student@test.com", "password": "TestPass123!"}