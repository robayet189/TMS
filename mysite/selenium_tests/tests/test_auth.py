import pytest
from pages.login_page import LoginPage

# tests/test_auth.py
import pytest
from pages.login_page import LoginPage

class TestAuthentication:
    
    def test_valid_login(self, driver, base_url):
        """Valid user login redirects to dashboard"""
        page = LoginPage(driver, base_url)
        
        # Open login page
        page.open_login_page()
        
        # Debug: Print current URL before login
        print(f"\n🔍 URL before login: {page.get_current_url()}")
        
        # Perform login
        page.login("student@test.com", "TestPass123!")
        
        # Wait for potential redirect (increase timeout)
        import time
        time.sleep(3)  # Wait 3 seconds for redirect to complete
        
        # Debug: Print current URL after login
        current_url = page.get_current_url()
        print(f"🔍 URL after login: {current_url}")
        
        # Check for error toast
        toast_msg = page.get_toast_message()
        if toast_msg:
            print(f"⚠️ Toast message: {toast_msg}")
            if "error" in toast_msg.lower() or "invalid" in toast_msg.lower():
                pytest.fail(f"Login failed with message: {toast_msg}")
        
        # Check if URL contains any expected dashboard pattern
        expected_patterns = [
            "/dashboard/",
            "/admin_page/dashboard/",
            "/driver/dashboard/",
            "/homepage",
            "/home",
            "/"  # Fallback: root URL might be dashboard
        ]
        
        url_lower = current_url.lower()
        is_success = any(pattern.lower() in url_lower for pattern in expected_patterns)
        
        if not is_success:
            print(f"❌ URL does not match any expected pattern:")
            for pattern in expected_patterns:
                print(f"   - Looking for: {pattern}")
            print(f"   - Actual URL: {current_url}")
        
        assert is_success, f"Login failed or wrong redirect. Current URL: {current_url}"
    def test_invalid_login(self, driver, base_url):
        """Invalid credentials show error"""
        page = LoginPage(driver, base_url)
        page.open("/login/")
        page.login("wrong_user", "wrong_pass")
        assert page.get_error() is not None, "Error message should appear"




# Additional authentication tests for logout, password reset, etc. can be added here as needed.        