import pytest
import random
import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC

class TestRegistration:
    def test_successful_registration(self, driver, base_url, wait):
        driver.get(f"{base_url}/register/")
        
        # Wait for registration form - flexible selector
        form_found = False
        for selector in [
            (By.NAME, "full_name"),
            (By.NAME, "username"),
            (By.NAME, "name"),
            (By.ID, "registerForm"),
            (By.CSS_SELECTOR, "form")
        ]:
            try:
                wait.until(EC.presence_of_element_located(selector))
                form_found = True
                break
            except:
                continue
        
        if not form_found:
            print("❌ Registration form not found. Available inputs:")
            inputs = driver.find_elements(By.TAG_NAME, "input")
            for inp in inputs[:10]:  # Show first 10
                print(f"  - name='{inp.get_attribute('name')}' id='{inp.get_attribute('id')}' placeholder='{inp.get_attribute('placeholder')}'")
            pytest.fail("Registration form not found")
        
        unique_id = random.randint(1000, 9999)
        
        # Fill form - try multiple field names
        fields = {
            "full_name": [f"Test User {unique_id}"],
            "username": [f"testuser{unique_id}"],
            "name": [f"Test User {unique_id}"],
            "email": [f"test{unique_id}@example.com"],
            "password": ["SecurePass123!"],
            "phone": [f"017{unique_id}0000"],
            "institution_type": ["university"],
            "user_type": ["student"],
            "institution_id": [f"STU{unique_id}"]
        }
        
        for field_name, values in fields.items():
            for value in values:
                for name_attr in [field_name, field_name.replace("_", "")]:
                    try:
                        element = driver.find_element(By.NAME, name_attr)
                        element.send_keys(value)
                        break
                    except:
                        continue
        
        # Submit - try multiple selectors
        submitted = False
        for selector in [
            (By.ID, "registerBtn"),
            (By.CSS_SELECTOR, "button[type='submit']"),
            (By.XPATH, "//button[contains(text(), 'Register')]"),
            (By.XPATH, "//input[@type='submit']")
        ]:
            try:
                driver.find_element(*selector).click()
                submitted = True
                break
            except:
                continue
        
        if not submitted:
            pytest.fail("Could not submit registration form")
        
        # Wait for redirect to account-created or login page
        try:
            wait.until(EC.url_contains("/account-created/"))
            assert "created" in driver.current_url.lower()
        except:
            # Fallback: check if redirected to login
            wait.until(EC.url_contains("/login/"))
            assert "/login/" in driver.current_url