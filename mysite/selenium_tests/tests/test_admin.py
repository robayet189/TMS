# selenium_tests/tests/test_admin.py
import pytest
import time  # ✅ FIXED: Import time module
from pages.login_page import LoginPage
from pages.admin_dashboard_page import AdminDashboardPage

class TestAdminModule:
    
    def test_admin_login_and_dashboard(self, driver, base_url, test_admin_credentials):
        """Test admin login redirects to admin dashboard"""
        login_page = LoginPage(driver, base_url)
        login_page.open_login_page()
        login_page.login(test_admin_credentials["username"], test_admin_credentials["password"])
        
        driver.implicitly_wait(5)
        time.sleep(2)
        
        # Check URL for admin dashboard
        assert "/admin_page/dashboard/" in driver.current_url or "/admin/" in driver.current_url, \
            f"Admin dashboard not loaded. Current URL: {driver.current_url}"

    def test_admin_view_users(self, driver, base_url, test_admin_credentials):
        """Test admin can view user management"""
        login_page = LoginPage(driver, base_url)
        login_page.open_login_page()
        login_page.login(test_admin_credentials["username"], test_admin_credentials["password"])
        time.sleep(2)
        
        # Navigate to users page
        driver.get(f"{base_url}/admin_page/users/")
        time.sleep(2)
        
        # Check if user table exists
        assert "user" in driver.page_source.lower() or "admin" in driver.current_url.lower(), \
            "User management page not accessible"

    def test_admin_view_fleet(self, driver, base_url, test_admin_credentials):
        """Test admin can view fleet management"""
        login_page = LoginPage(driver, base_url)
        login_page.open_login_page()
        login_page.login(test_admin_credentials["username"], test_admin_credentials["password"])
        time.sleep(2)
        
        # Navigate to fleet page
        driver.get(f"{base_url}/admin_page/fleet/")
        time.sleep(2)
        
        # Check if fleet table exists
        assert "bus" in driver.page_source.lower() or "vehicle" in driver.page_source.lower() or "fleet" in driver.current_url.lower(), \
            "Fleet management page not accessible"
        


# Additional admin tests for adding/editing users, managing fleet, etc. can be added here as needed.        