import pytest
import random
from pages.register_page import RegisterPage

class TestRegistration:
    def test_successful_registration(self, driver, base_url):
        """Register with valid data & verify success toast"""
        page = RegisterPage(driver, base_url)
        page.open("/register/")
        
       
        unique_id = str(random.randint(1000, 9999))
        page.register(
            full_name="Selenium Test User",
            email=f"test_{unique_id}@example.com",
            password="SecurePass123!",
            phone="01700000000",
            inst_type="Educational",
            user_type="Student",
            inst_id=f"2024-1-60-{unique_id}"
        )
        
        
        msg = page.get_toast_message()
        assert msg is not None, "Success toast not shown"
        assert "success" in msg.lower() or "created" in msg.lower(), f"Unexpected message: {msg}"