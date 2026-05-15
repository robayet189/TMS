import pytest
from pages.login_page import LoginPage
from pages.register_page import RegisterPage
from pages.dashboard_page import DashboardPage
import time

class TestAuthentication:
    """Test authentication functionality"""
    
    @pytest.fixture(autouse=True)
    def setup(self, setup):
        """Setup test fixtures"""
        self.driver = setup['driver']
        self.base_url = setup['base_url']
        self.login_page = LoginPage(self.driver, self.base_url)
        self.register_page = RegisterPage(self.driver, self.base_url)
        self.dashboard_page = DashboardPage(self.driver, self.base_url)
    
    def test_valid_login(self):
        """Test valid user login"""
        self.login_page.open_login_page()
        self.login_page.login("student@test.com", "TestPass123!")
        time.sleep(2)
        
        assert self.dashboard_page.is_dashboard_loaded(), "Dashboard did not load after login"
        assert "/dashboard/" in self.driver.current_url
    
    def test_invalid_login(self):
        """Test invalid login credentials"""
        self.login_page.open_login_page()
        self.login_page.login("invalid@test.com", "WrongPass")
        time.sleep(2)
        
        # Should stay on login page or show error
        assert "/login/" in self.driver.current_url or self.login_page.is_element_present(*self.login_page.ERROR_MESSAGE)
    
    def test_user_registration(self):
        """Test new user registration"""
        import random
        timestamp = str(int(time.time()))
        
        self.register_page.open_register_page()
        self.register_page.register(
            full_name=f"Test User {timestamp}",
            email=f"test{timestamp}@test.com",
            phone="01712345678",
            password="TestPass123!"
        )
        time.sleep(2)
        
        # Check if redirected to login or account created page
        assert "/login/" in self.driver.current_url or "/account-created/" in self.driver.current_url
    
    def test_logout(self):
        """Test user logout"""
        # Login first
        self.login_page.open_login_page()
        self.login_page.login("student@test.com", "TestPass123!")
        time.sleep(2)
        
        # Logout
        self.dashboard_page.click_logout()
        time.sleep(2)
        
        # Should be redirected to login or homepage
        assert "/login/" in self.driver.current_url or self.driver.current_url == self.base_url + "/"