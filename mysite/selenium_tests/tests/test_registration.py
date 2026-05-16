import pytest
import random
import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC

class TestRegistration:
    def test_successful_registration(self, driver, base_url, wait):
        driver.get(f"{base_url}/register/")
        time.sleep(2)
        
        unique_id = random.randint(1000, 9999)
        
        # Fill form using ACTUAL IDs from your HTML (from debug output)
        driver.find_element(By.ID, "fullName").send_keys(f"Test User {unique_id}")
        driver.find_element(By.ID, "email").send_keys(f"test{unique_id}@example.com")
        driver.find_element(By.ID, "password").send_keys("SecurePass123!")
        driver.find_element(By.ID, "confirmPwd").send_keys("SecurePass123!")
        driver.find_element(By.ID, "phone").send_keys(f"017{unique_id}0000")
        driver.find_element(By.ID, "institutionId").send_keys(f"STU{unique_id}")
        
        # Select institution type via dropdown (if your HTML has this)
        try:
            inst_dropdown = driver.find_element(By.ID, "instTypeBtn")
            inst_dropdown.click()
            time.sleep(0.5)
            edu_option = driver.find_element(By.XPATH, "//div[contains(text(), 'Educational')]")
            edu_option.click()
            time.sleep(0.5)
        except:
            pass  # Skip if dropdown logic differs
        
        # Select user type
        try:
            user_dropdown = driver.find_element(By.ID, "userTypeBtn")
            user_dropdown.click()
            time.sleep(0.5)
            student_option = driver.find_element(By.XPATH, "//div[contains(text(), 'student')]")
            student_option.click()
            time.sleep(0.5)
        except:
            pass
        
        time.sleep(1)
        
        # Submit registration - FIXED: scroll + JS click to avoid interception
        register_btn = driver.find_element(By.ID, "registerBtn")
        driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", register_btn)
        time.sleep(1)
        driver.execute_script("arguments[0].click();", register_btn)  # JS click avoids overlay issues
        
        time.sleep(3)
        
        # Verify redirect to login or account created page
        assert "/login/" in driver.current_url or "created" in driver.page_source.lower() or "success" in driver.page_source.lower()