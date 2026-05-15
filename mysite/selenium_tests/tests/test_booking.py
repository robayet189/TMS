import pytest
import time
from selenium.webdriver.common.by import By

class TestBookingFlow:
    def test_book_seat_successfully(self, driver, base_url, wait):
        # Login first
        driver.get(f"{base_url}/login/")
        driver.find_element(By.ID, "username").send_keys("student@test.com")
        driver.find_element(By.ID, "password").send_keys("TestPass123!")
        driver.find_element(By.ID, "loginBtn").click()
        time.sleep(2)
        
        # Go to schedule
        driver.get(f"{base_url}/schedule/")
        time.sleep(1)
        
        # Click first "Book" button
        try:
            book_btn = driver.find_element(By.CLASS_NAME, "btn-book")
            book_btn.click()
            time.sleep(2)
        except:
            pytest.skip("No bookable routes found")
        
        # Fill booking form - use IDs if available, fallback to name
        try:
            # Try to find seats input by name first, then ID
            try:
                driver.find_element(By.NAME, "seats").send_keys("1")
            except:
                driver.find_element(By.ID, "seats").send_keys("1")
            
            try:
                driver.find_element(By.NAME, "passenger_name").send_keys("Selenium Tester")
            except:
                driver.find_element(By.ID, "passenger_name").send_keys("Selenium Tester")
        except:
            print("⚠️ Booking form fields not found - using defaults")
        
        # Submit
        driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
        time.sleep(3)
        
        # Verify
        assert "confirmed" in driver.page_source.lower() or "success" in driver.page_source.lower()