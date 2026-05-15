import pytest
import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC

class TestAuthentication:
    def test_valid_login(self, driver, base_url, wait):
        driver.get(f"{base_url}/login/")
        time.sleep(1)
        
        # ✅ Use ACTUAL selectors from debug output
        driver.find_element(By.ID, "username").send_keys("student@test.com")
        driver.find_element(By.ID, "password").send_keys("TestPass123!")
        driver.find_element(By.ID, "loginBtn").click()
        
        time.sleep(2)
        assert "dashboard" in driver.current_url.lower()

    def test_logout(self, driver, base_url, wait):
        # Login first
        driver.get(f"{base_url}/login/")
        driver.find_element(By.ID, "username").send_keys("student@test.com")
        driver.find_element(By.ID, "password").send_keys("TestPass123!")
        driver.find_element(By.ID, "loginBtn").click()
        time.sleep(2)
        
        # Find logout - try form submit first (most reliable)
        try:
            logout_form = driver.find_element(By.XPATH, "//form[contains(@action, 'logout')]")
            driver.execute_script("arguments[0].submit();", logout_form)
        except:
            # Fallback: click logout button/link
            driver.find_element(By.XPATH, "//*[contains(text(), 'Logout') or contains(text(), 'Log out')]").click()
        
        time.sleep(2)
        assert "/login/" in driver.current_url