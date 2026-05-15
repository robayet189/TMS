from selenium.webdriver.common.by import By
from .base_page import BasePage

class DashboardPage(BasePage):
    """Dashboard page object"""
    
    # Locators
    WELCOME_MESSAGE = (By.XPATH, "//h1[contains(text(), 'Welcome')]")
    TOTAL_BOOKINGS_CARD = (By.CLASS_NAME, "stat-card")
    NAVIGATION_MENU = (By.CLASS_NAME, "nav")
    SCHEDULE_LINK = (By.XPATH, "//a[contains(text(), 'Schedule')]")
    PROFILE_LINK = (By.XPATH, "//a[contains(text(), 'Profile')]")
    BOOKINGS_LINK = (By.XPATH, "//a[contains(text(), 'My Bookings')]")
    LOGOUT_BUTTON = (By.XPATH, "//button[contains(text(), 'Logout')]")
    
    def __init__(self, driver, base_url):
        super().__init__(driver, base_url)
    
    def is_dashboard_loaded(self):
        """Check if dashboard is loaded"""
        return self.is_element_present(*self.WELCOME_MESSAGE)
    
    def get_welcome_message(self):
        """Get welcome message"""
        return self.get_element_text(self.WELCOME_MESSAGE)
    
    def click_schedule(self):
        """Click schedule link"""
        self.click_element(self.SCHEDULE_LINK)
    
    def click_profile(self):
        """Click profile link"""
        self.click_element(self.PROFILE_LINK)
    
    def click_my_bookings(self):
        """Click my bookings link"""
        self.click_element(self.BOOKINGS_LINK)
    
    def click_logout(self):
        """Click logout button"""
        self.click_element(self.LOGOUT_BUTTON)