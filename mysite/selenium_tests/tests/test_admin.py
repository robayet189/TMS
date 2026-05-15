import pytest
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC

class TestAdminModule:
    def test_admin_login_and_dashboard(self, driver, base_url, wait):
        driver.get(f"{base_url}/login/")
        wait.until(EC.presence_of_element_located((By.NAME, "username"))).send_keys("admin@test.com")
        driver.find_element(By.NAME, "password").send_keys("AdminPass123!")
        driver.find_element(By.ID, "loginBtn").click()
        wait.until(EC.url_contains("/admin_page/dashboard/"))
        assert "admin" in driver.current_url.lower()

    def test_admin_view_users(self, driver, base_url, wait):
        driver.get(f"{base_url}/login/")
        wait.until(EC.presence_of_element_located((By.NAME, "username"))).send_keys("admin@test.com")
        driver.find_element(By.NAME, "password").send_keys("AdminPass123!")
        driver.find_element(By.ID, "loginBtn").click()
        wait.until(EC.url_contains("/admin_page/dashboard/"))
        
        driver.get(f"{base_url}/admin_page/users/")
        wait.until(EC.presence_of_element_located((By.TAG_NAME, "table")))
        assert "users" in driver.current_url

    def test_admin_view_fleet(self, driver, base_url, wait):
        driver.get(f"{base_url}/login/")
        wait.until(EC.presence_of_element_located((By.NAME, "username"))).send_keys("admin@test.com")
        driver.find_element(By.NAME, "password").send_keys("AdminPass123!")
        driver.find_element(By.ID, "loginBtn").click()
        wait.until(EC.url_contains("/admin_page/dashboard/"))
        
        driver.get(f"{base_url}/admin_page/fleet/")
        wait.until(EC.presence_of_element_located((By.TAG_NAME, "table")))
        assert "fleet" in driver.current_url