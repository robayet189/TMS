import pytest
import random
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC

class TestRegistration:
    def test_successful_registration(self, driver, base_url, wait):
        driver.get(f"{base_url}/register/")
        wait.until(EC.presence_of_element_located((By.NAME, "full_name")))
        
        unique_id = random.randint(1000, 9999)
        driver.find_element(By.NAME, "full_name").send_keys(f"Test User {unique_id}")
        driver.find_element(By.NAME, "email").send_keys(f"test{unique_id}@example.com")
        driver.find_element(By.NAME, "password").send_keys("SecurePass123!")
        driver.find_element(By.NAME, "phone").send_keys(f"017{unique_id}0000")
        driver.find_element(By.NAME, "institution_type").send_keys("university")
        driver.find_element(By.NAME, "user_type").send_keys("student")
        driver.find_element(By.NAME, "institution_id").send_keys(f"STU{unique_id}")
        
        driver.find_element(By.ID, "registerBtn").click()
        wait.until(EC.url_contains("/account-created/"))
        assert "created" in driver.current_url.lower()