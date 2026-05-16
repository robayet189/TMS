from selenium.webdriver.common.by import By
from .base_page import BasePage

class RegisterPage(BasePage):
    """Register page object"""
    
    # Locators
    FULL_NAME_INPUT = (By.NAME, "full_name")
    EMAIL_INPUT = (By.NAME, "email")
    PHONE_INPUT = (By.NAME, "phone")
    PASSWORD_INPUT = (By.NAME, "password")
    CONFIRM_PASSWORD_INPUT = (By.NAME, "confirm_password")
    USER_TYPE_SELECT = (By.NAME, "user_type")
    REGISTER_BUTTON = (By.XPATH, "//button[@type='submit']")
    
    def __init__(self, driver, base_url):
        super().__init__(driver, base_url)
    
    def open_register_page(self):
        """Open register page"""
        self.open_url("/register/")
    
    def enter_full_name(self, name):
        """Enter full name"""
        self.enter_text(self.FULL_NAME_INPUT, name)
    
    def enter_email(self, email):
        """Enter email"""
        self.enter_text(self.EMAIL_INPUT, email)
    
    def enter_phone(self, phone):
        """Enter phone"""
        self.enter_text(self.PHONE_INPUT, phone)
    
    def enter_password(self, password):
        """Enter password"""
        self.enter_text(self.PASSWORD_INPUT, password)
    
    def enter_confirm_password(self, password):
        """Enter confirm password"""
        self.enter_text(self.CONFIRM_PASSWORD_INPUT, password)
    
    def select_user_type(self, user_type):
        """Select user type"""
        self.click_element(self.USER_TYPE_SELECT)
        # Implementation depends on your select element type
    
    def click_register(self):
        """Click register button"""
        self.click_element(self.REGISTER_BUTTON)
    
    def register(self, full_name, email, phone, password, user_type="student"):
        """Complete registration process"""
        self.enter_full_name(full_name)
        self.enter_email(email)
        self.enter_phone(phone)
        self.enter_password(password)
        self.enter_confirm_password(password)
        self.click_register()