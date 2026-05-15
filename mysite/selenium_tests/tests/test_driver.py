import pytest
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC

class TestDriverModule:
    def test_driver_login_and_trip_view(self, driver, base_url, wait):
        driver.get(f"{base_url}/login/")
        wait.until(EC.presence_of_element_located((By.NAME, "username"))).send_keys("driver@test.com")
        driver.find_element(By.NAME, "password").send_keys("DriverPass123!")
        driver.find_element(By.ID, "loginBtn").click()
        wait.until(EC.url_contains("/driver/dashboard/"))
        assert "driver" in driver.current_url.lower()
        
        # Verify trip cards load
        wait.until(EC.presence_of_element_located((By.CLASS_NAME, "trip-card")))
        assert driver.find_elements(By.CLASS_NAME, "trip-card")