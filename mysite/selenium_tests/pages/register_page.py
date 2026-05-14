from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC  # ✅ Must have this line
from .base_page import BasePage
import time
import random

class RegisterPage(BasePage):
    FULL_NAME = (By.ID, "fullName")
    EMAIL = (By.ID, "email")
    PASSWORD = (By.ID, "password")
    CONFIRM_PWD = (By.ID, "confirmPwd")
    PHONE = (By.ID, "phone")
    INST_TYPE_BTN = (By.ID, "instTypeBtn")
    USER_TYPE_BTN = (By.ID, "userTypeBtn")
    INST_ID = (By.ID, "institutionId")
    REGISTER_BTN = (By.CSS_SELECTOR, ".btn-register")
    TOAST_MSG = (By.ID, "toastMsg")

    def register(self, full_name, email, password, phone, inst_type, user_type, inst_id):
        self.enter_text(self.FULL_NAME, full_name)
        self.enter_text(self.EMAIL, email)
        self.enter_text(self.PASSWORD, password)
        self.enter_text(self.CONFIRM_PWD, password)
        self.enter_text(self.PHONE, phone)
        
        # Custom Dropdown: Institution Type
        self.click(self.INST_TYPE_BTN)
        inst_menu = (By.ID, "instTypeMenu")
        self.wait.until(EC.visibility_of_element_located(inst_menu))
        option = (By.XPATH, f"//div[@id='instTypeMenu']//div[contains(text(), '{inst_type}')]")
        self.click(option)
        
        # Custom Dropdown: User Type
        self.click(self.USER_TYPE_BTN)
        user_menu = (By.ID, "userTypeMenu")
        self.wait.until(EC.visibility_of_element_located(user_menu))
        option = (By.XPATH, f"//div[@id='userTypeMenu']//div[contains(text(), '{user_type}')]")
        self.click(option)
        
        self.enter_text(self.INST_ID, inst_id)
        self.click(self.REGISTER_BTN)

    def get_toast_message(self):
        return self.get_text(self.TOAST_MSG) if self.is_visible(self.TOAST_MSG) else None