import pytest
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC

class TestBookingFlow:
    def test_book_seat_successfully(self, driver, base_url, wait):
        # Login
        driver.get(f"{base_url}/login/")
        wait.until(EC.presence_of_element_located((By.NAME, "username"))).send_keys("student@test.com")
        driver.find_element(By.NAME, "password").send_keys("TestPass123!")
        driver.find_element(By.ID, "loginBtn").click()
        wait.until(EC.url_contains("/dashboard/"))
        
        # Navigate to Schedule
        driver.get(f"{base_url}/schedule/")
        wait.until(EC.presence_of_element_located((By.CLASS_NAME, "route-card")))
        
        # Click Book Button
        book_btn = wait.until(EC.element_to_be_clickable((By.CLASS_NAME, "btn-book")))
        book_btn.click()
        
        # Fill Booking Form
        wait.until(EC.presence_of_element_located((By.NAME, "seats")))
        driver.find_element(By.NAME, "seats").send_keys("1")
        driver.find_element(By.NAME, "passenger_name").send_keys("Selenium Tester")
        driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
        
        # Verify Success
        wait.until(EC.text_to_be_present_in_element((By.TAG_NAME, "body"), "confirmed"))
        assert "confirmed" in driver.page_source.lower()

    def test_cancel_booking(self, driver, base_url, wait):
        # Login & go to bookings
        driver.get(f"{base_url}/login/")
        wait.until(EC.presence_of_element_located((By.NAME, "username"))).send_keys("student@test.com")
        driver.find_element(By.NAME, "password").send_keys("TestPass123!")
        driver.find_element(By.ID, "loginBtn").click()
        wait.until(EC.url_contains("/dashboard/"))
        
        driver.get(f"{base_url}/my-bookings/")
        wait.until(EC.presence_of_element_located((By.TAG_NAME, "table")))
        
        if "No bookings" in driver.page_source:
            pytest.skip("No active bookings to cancel")
            
        cancel_btn = wait.until(EC.element_to_be_clickable((By.CLASS_NAME, "btn-cancel")))
        cancel_btn.click()
        wait.until(EC.alert_is_present())
        driver.switch_to.alert.accept()
        wait.until(EC.text_to_be_present_in_element((By.TAG_NAME, "body"), "cancelled"))
        assert "cancelled" in driver.page_source.lower()