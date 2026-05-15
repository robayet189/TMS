import pytest
import random
import time
from selenium.webdriver.common.by import By

class TestRegistration:
    def test_successful_registration(self, driver, base_url, wait):
        driver.get(f"{base_url}/register/")
        time.sleep(1)
        
        unique_id = random.randint(1000, 9999)
        
        # ✅ Use ACTUAL IDs from debug output (NO name attributes in HTML)
        driver.find_element(By.ID, "fullName").send_keys(f"Test User {unique_id}")
        driver.find_element(By.ID, "email").send_keys(f"test{unique_id}@example.com")
        driver.find_element(By.ID, "password").send_keys("SecurePass123!")
        driver.find_element(By.ID, "confirmPwd").send_keys("SecurePass123!")
        driver.find_element(By.ID, "phone").send_keys(f"017{unique_id}0000")
        driver.find_element(By.ID, "institutionId").send_keys(f"STU{unique_id}")
        
        # Submit using actual button ID
        driver.find_element(By.ID, "registerBtn").click()
        time.sleep(3)
        
        # Check for success
        assert "created" in driver.page_source.lower() or "/login/" in driver.current_url