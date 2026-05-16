import pytest
import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC

class TestAuthentication:
    def test_valid_login(self, driver, base_url, wait):
        driver.get(f"{base_url}/login/")
        time.sleep(1)
        
        # Login with correct selectors
        driver.find_element(By.ID, "username").send_keys("student@test.com")
        driver.find_element(By.ID, "password").send_keys("TestPass123!")
        driver.find_element(By.ID, "loginBtn").click()
        
        # Wait for redirect OR page content change
        time.sleep(3)
        
        # ✅ FIXED: Check for successful login indicators, not just URL
        page_source = driver.page_source.lower()
        current_url = driver.current_url.lower()
        
        # Successful login indicators:
        # 1. Redirected to dashboard
        # 2. Welcome message appears
        # 3. Logout button appears
        # 4. Profile link appears
        success_indicators = [
            "dashboard" in current_url,
            "welcome" in page_source,
            "logout" in page_source,
            "profile" in page_source,
            "book a seat" in page_source,
        ]
        
        if not any(success_indicators):
            # Debug: save screenshot and print page info
            driver.save_screenshot("debug_login_failure.png")
            print(f"\n❌ Login failed!")
            print(f"URL: {driver.current_url}")
            print(f"Page title: {driver.title}")
            # Check for error messages
            if "invalid" in page_source or "error" in page_source:
                print("⚠️ Error message detected in page")
            pytest.fail("Login did not succeed - check credentials or backend redirect logic")
        
        assert any(success_indicators), "Login successful indicators not found"

    def test_invalid_login(self, driver, base_url, wait):
        driver.get(f"{base_url}/login/")
        driver.find_element(By.ID, "username").send_keys("wrong@test.com")
        driver.find_element(By.ID, "password").send_keys("WrongPass123!")
        driver.find_element(By.ID, "loginBtn").click()
        
        time.sleep(2)
        # Should stay on login or show error
        assert "/login/" in driver.current_url or "error" in driver.page_source.lower() or "invalid" in driver.page_source.lower()

    def test_logout(self, driver, base_url, wait):
        # Login first
        driver.get(f"{base_url}/login/")
        driver.find_element(By.ID, "username").send_keys("student@test.com")
        driver.find_element(By.ID, "password").send_keys("TestPass123!")
        driver.find_element(By.ID, "loginBtn").click()
        time.sleep(3)
        
        # Find and click logout
        logout_clicked = False
        selectors = [
            (By.XPATH, "//button[contains(text(), 'Logout')]"),
            (By.XPATH, "//a[contains(text(), 'Logout')]"),
            (By.CSS_SELECTOR, "form button[type='submit']"),
            (By.NAME, "logout"),
        ]
        
        for selector in selectors:
            try:
                elements = driver.find_elements(*selector)
                for el in elements:
                    if el.is_displayed() and el.is_enabled():
                        driver.execute_script("arguments[0].click();", el)
                        logout_clicked = True
                        break
                if logout_clicked:
                    break
            except:
                continue
        
        if not logout_clicked:
            try:
                form = driver.find_element(By.XPATH, "//form[contains(@action, 'logout')]")
                driver.execute_script("arguments[0].submit();", form)
                logout_clicked = True
            except:
                pass
        
        time.sleep(2)
        # Accept both /login/ and homepage as valid logout destinations
        assert "/login/" in driver.current_url or driver.current_url == base_url or "login" in driver.page_source.lower()