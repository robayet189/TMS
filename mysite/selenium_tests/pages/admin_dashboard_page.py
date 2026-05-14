# selenium_tests/pages/admin_dashboard_page.py
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from .base_page import BasePage
import time

class AdminDashboardPage(BasePage):
    """
    Page Object Model for Admin Dashboard
    """
    
    # ==================== LOCATORS ====================
    # ✅ FIXED: Removed invalid :contains() selector
    DASHBOARD_TITLE = (By.CSS_SELECTOR, "h1.page-title, .page-header h1, h1")
    
    # ✅ Use text-based XPath instead of invalid CSS :contains()
    USERS_MENU = (By.XPATH, "//a[contains(text(), 'Users')] | //a[@href*='users'] | //nav//a[contains(., 'User')]")
    FLEET_MENU = (By.XPATH, "//a[contains(text(), 'Fleet')] | //a[@href*='fleet'] | //nav//a[contains(., 'Bus')]")
    SCHEDULE_MENU = (By.XPATH, "//a[contains(text(), 'Schedule')] | //a[@href*='schedule']")
    
    USERS_TABLE = (By.CSS_SELECTOR, ".user-table, table.data-table, table")
    BUSES_TABLE = (By.CSS_SELECTOR, ".fleet-table, table.data-table, table")
    ADD_BUS_BTN = (By.CSS_SELECTOR, ".btn-add-bus, button:contains('Add Bus'), .btn-primary")
    
    # ==================== METHODS ====================
    
    def is_admin_dashboard_loaded(self):
        """Check if admin dashboard is loaded"""
        try:
            return self.wait.until(EC.presence_of_element_located(self.DASHBOARD_TITLE)).is_displayed()
        except:
            # Fallback: check URL
            return "/admin_page/dashboard/" in self.driver.current_url
    
    def navigate_to_users(self):
        """Navigate to users management page"""
        # Try multiple locator strategies
        locators = [
            (By.XPATH, "//a[contains(text(), 'Users')]"),
            (By.XPATH, "//a[@href*='users']"),
            (By.CSS_SELECTOR, "a[href*='users']"),
            (By.LINK_TEXT, "Users"),
        ]
        
        for locator in locators:
            try:
                element = self.wait.until(EC.element_to_be_clickable(locator))
                self._smart_click(element)
                time.sleep(1)  # Wait for page load
                return True
            except:
                continue
        raise Exception("Users menu not found - check your admin HTML")
    
    def navigate_to_fleet(self):
        """Navigate to fleet management page"""
        locators = [
            (By.XPATH, "//a[contains(text(), 'Fleet')]"),
            (By.XPATH, "//a[contains(text(), 'Bus')]"),
            (By.XPATH, "//a[@href*='fleet']"),
            (By.CSS_SELECTOR, "a[href*='fleet']"),
            (By.LINK_TEXT, "Fleet"),
        ]
        
        for locator in locators:
            try:
                element = self.wait.until(EC.element_to_be_clickable(locator))
                self._smart_click(element)
                time.sleep(1)
                return True
            except:
                continue
        raise Exception("Fleet menu not found - check your admin HTML")
    
    def is_users_table_visible(self):
        """Check if users table is visible"""
        try:
            return self.wait.until(EC.presence_of_element_located(self.USERS_TABLE)).is_displayed()
        except:
            return False
    
    def is_fleet_table_visible(self):
        """Check if fleet table is visible"""
        try:
            return self.wait.until(EC.presence_of_element_located(self.BUSES_TABLE)).is_displayed()
        except:
            return False