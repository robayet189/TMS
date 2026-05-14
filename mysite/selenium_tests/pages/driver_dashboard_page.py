# selenium_tests/pages/driver_dashboard_page.py
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from .base_page import BasePage
import time

class DriverDashboardPage(BasePage):
    """
    Page Object Model for Driver Dashboard
    """
    
    # ==================== LOCATORS ====================
    DASHBOARD_TITLE = (By.CSS_SELECTOR, "h1.driver-title, .driver-header h1, h1")
    TRIP_LIST = (By.CSS_SELECTOR, ".trip-list, .schedule-item, table.trip-table, .card")
    START_TRIP_BTN = (By.CSS_SELECTOR, ".btn-start-trip, button:contains('Start Trip'), .btn-primary")
    TRIP_STATUS = (By.CSS_SELECTOR, ".trip-status, .status-badge, .badge")
    DRIVER_URL_PATTERNS = ["/driver/dashboard/", "/driver/", "/dashboard/"]

    def is_driver_dashboard_loaded(self):
        """Check if driver dashboard is loaded"""
        try:
            return self.wait.until(EC.presence_of_element_located(self.DASHBOARD_TITLE)).is_displayed()
        except:
            # Fallback: check URL
            return any(pattern in self.driver.current_url for pattern in self.DRIVER_URL_PATTERNS)

    def is_trip_list_visible(self):
        """Check if trip list is visible"""
        try:
            return self.wait.until(EC.presence_of_element_located(self.TRIP_LIST)).is_displayed()
        except:
            return False

    def click_start_trip(self):
        """Click start trip button"""
        try:
            btn = self.wait.until(EC.element_to_be_clickable(self.START_TRIP_BTN))
            self._smart_click(btn)
            time.sleep(1)
            return True
        except:
            return False

    def get_trip_status(self):
        """Get current trip status text"""
        try:
            return self.wait.until(EC.visibility_of_element_located(self.TRIP_STATUS)).text
        except:
            return "Unknown"