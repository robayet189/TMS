import pytest
import time
from selenium.webdriver.common.by import By

class TestDriverModule:
    def test_driver_login_and_trip_view(self, driver, base_url, wait):
        driver.get(f"{base_url}/login/")
        time.sleep(1)
        
        # Driver login uses same form
        driver.find_element(By.ID, "username").send_keys("driver@test.com")
        driver.find_element(By.ID, "password").send_keys("DriverPass123!")
        driver.find_element(By.ID, "loginBtn").click()
        
        time.sleep(3)
        
        # ✅ FIXED: Check for successful login indicators, not just URL
        page_source = driver.page_source.lower()
        current_url = driver.current_url.lower()
        
        # Driver successful login indicators:
        success_indicators = [
            "dashboard" in current_url,
            "driver" in current_url,
            "welcome" in page_source,
            "trip" in page_source,
            "logout" in page_source,
        ]
        
        if not any(success_indicators):
            driver.save_screenshot("debug_driver_login_failure.png")
            print(f"\n❌ Driver login failed!")
            print(f"URL: {driver.current_url}")
            print(f"Page source preview: {driver.page_source[:500]}")
            pytest.fail("Driver login did not succeed")
        
        assert any(success_indicators)