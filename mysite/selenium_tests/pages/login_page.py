from selenium.webdriver.common.by import By
from .base_page import BasePage

class LoginPage(BasePage):
    """Login page object"""
    
    # Locators
    USERNAME_INPUT = (By.NAME, "username")
    PASSWORD_INPUT = (By.NAME, "password")
    LOGIN_BUTTON = (By.XPATH, "//button[@type='submit']")
    ERROR_MESSAGE = (By.CLASS_NAME, "error-message")
    
    def __init__(self, driver, base_url):
        super().__init__(driver, base_url)
    
    def open_login_page(self):
        """Open login page"""
        self.open_url("/login/")
    
    def enter_username(self, username):
        """Enter username"""
        self.enter_text(self.USERNAME_INPUT, username)
    
    def enter_password(self, password):
        """Enter password"""
        self.enter_text(self.PASSWORD_INPUT, password)
    
    def click_login(self):
        """Click login button"""
        self.click_element(self.LOGIN_BUTTON)
    
    def login(self, username, password):
        """Complete login process"""
        self.enter_username(username)
        self.enter_password(password)
        self.click_login()
    
    def get_error_message(self):
        """Get error message"""
        return self.get_element_text(self.ERROR_MESSAGE)
    
    def is_login_successful(self):
        """Check if login was successful"""
        return "/dashboard/" in self.get_current_url()