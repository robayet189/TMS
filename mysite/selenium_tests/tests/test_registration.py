import pytest
import random
import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

class TestRegistration:
    def test_successful_registration(self, driver, base_url, wait):
        driver.get(f"{base_url}/register/")
        
        # Wait for ANY form to load
        try:
            wait.until(EC.presence_of_element_located((By.TAG_NAME, "form")))
        except TimeoutException:
            print("❌ No form found on register page")
            print("Available inputs:", [inp.get_attribute("name") for inp in driver.find_elements(By.TAG_NAME, "input")[:10]])
            pytest.fail("Registration form not found")
        
        unique_id = random.randint(1000, 9999)
        
        # Smart field mapping - try multiple name variations
        field_mapping = {
            "name": ["full_name", "name", "username", "first_name"],
            "email": ["email"],
            "password": ["password", "pass"],
            "phone": ["phone", "mobile", "contact"],
            "institution_type": ["institution_type", "institution"],
            "user_type": ["user_type", "role"],
            "institution_id": ["institution_id", "student_id", "id"]
        }
        
        # Fill each field
        for field_key, possible_names in field_mapping.items():
            value_map = {
                "name": f"Test User {unique_id}",
                "email": f"test{unique_id}@example.com",
                "password": "SecurePass123!",
                "phone": f"017{unique_id}0000",
                "institution_type": "university",
                "user_type": "student",
                "institution_id": f"STU{unique_id}"
            }
            value = value_map.get(field_key)
            if not value:
                continue
                
            filled = False
            for name_attr in possible_names:
                try:
                    element = driver.find_element(By.NAME, name_attr)
                    if element.is_displayed():
                        element.clear()
                        element.send_keys(value)
                        filled = True
                        break
                except:
                    continue
            
            if not filled:
                print(f"⚠️ Could not fill field '{field_key}' with names {possible_names}")
        
        # Submit form - try EVERY possible submit method
        submitted = False
        
        # Method 1: Click submit button
        submit_selectors = [
            (By.ID, "registerBtn"),
            (By.CSS_SELECTOR, "button[type='submit']"),
            (By.XPATH, "//button[contains(text(), 'Register')]"),
            (By.XPATH, "//input[@type='submit']"),
            (By.CSS_SELECTOR, "form button"),
            (By.XPATH, "//button")
        ]
        
        for selector in submit_selectors:
            try:
                btn = driver.find_element(*selector)
                if btn.is_displayed() and btn.is_enabled():
                    btn.click()
                    submitted = True
                    break
            except:
                continue
        
        # Method 2: Submit form via JavaScript if button click fails
        if not submitted:
            try:
                form = driver.find_element(By.TAG_NAME, "form")
                driver.execute_script("arguments[0].submit();", form)
                submitted = True
            except:
                pass
        
        # Method 3: Press Enter in last field
        if not submitted:
            try:
                inputs = driver.find_elements(By.TAG_NAME, "input")
                if inputs:
                    inputs[-1].send_keys("\n")
                    submitted = True
            except:
                pass
        
        if not submitted:
            print("❌ Could not submit form. Available buttons:")
            buttons = driver.find_elements(By.TAG_NAME, "button")
            for btn in buttons:
                print(f"  - text='{btn.text}' type='{btn.get_attribute('type')}' class='{btn.get_attribute('class')}'")
            driver.save_screenshot("debug_registration_submit.png")
            pytest.fail("Could not submit registration form")
        
        # Wait for redirect with flexible check
        try:
            wait.until(lambda d: 
                "/account-created/" in d.current_url or 
                "/login/" in d.current_url or
                "created" in d.page_source.lower() or
                "success" in d.page_source.lower(),
                timeout=15
            )
        except TimeoutException:
            driver.save_screenshot("debug_registration_redirect.png")
            print(f"❌ Redirect failed. URL: {driver.current_url}")
            pytest.fail("Registration redirect timeout")
        
        # Final assertion
        assert "/account-created/" in driver.current_url or "/login/" in driver.current_url or "created" in driver.page_source.lower()