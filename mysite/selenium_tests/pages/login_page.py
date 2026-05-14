# selenium_tests/pages/login_page.py
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from .base_page import BasePage
import time

class LoginPage(BasePage):
    USERNAME_INPUT = (By.CSS_SELECTOR, '[data-testid="username-input"]')
    PASSWORD_INPUT = (By.CSS_SELECTOR, '[data-testid="password-input"]')
    LOGIN_BUTTON = (By.CSS_SELECTOR, '[data-testid="login-button"]')
    TOAST_MESSAGE = (By.CSS_SELECTOR, '[data-testid="toast-message"]')
    
    USERNAME_INPUT_FALLBACK = [
        (By.NAME, "username"), (By.ID, "username"), (By.CSS_SELECTOR, "input[name='username']"),
    ]
    PASSWORD_INPUT_FALLBACK = [
        (By.NAME, "password"), (By.ID, "password"), (By.CSS_SELECTOR, "input[type='password']"),
    ]
    LOGIN_BUTTON_FALLBACK = [
        (By.CSS_SELECTOR, "button[type='submit']"), (By.CSS_SELECTOR, "input[type='submit']"),
        (By.CSS_SELECTOR, ".btn-login"), (By.XPATH, "//button[contains(text(), 'Sign In')]"),
    ]
    
    def _find_first_available(self, locators_list, timeout=10):
        for locator in locators_list:
            try:
                return self.find(locator, timeout)
            except:
                continue
        return None
    
    def _find_clickable_first(self, locators_list, timeout=10):
        for locator in locators_list:
            try:
                return self.find_clickable(locator, timeout)
            except:
                continue
        return None
    
    def open_login_page(self):
        self.open("/login/")
        self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "form, #loginForm")))
        time.sleep(1)
    
    def enter_username(self, username):
        try:
            element = self.find(self.USERNAME_INPUT)
            element.clear(); element.send_keys(username); return
        except:
            pass
        element = self._find_first_available(self.USERNAME_INPUT_FALLBACK)
        if element:
            element.clear(); element.send_keys(username)
    
    def enter_password(self, password):
        try:
            element = self.find(self.PASSWORD_INPUT)
            element.clear(); element.send_keys(password); return
        except:
            pass
        element = self._find_first_available(self.PASSWORD_INPUT_FALLBACK)
        if element:
            element.clear(); element.send_keys(password)
    
    def click_login_button(self):
        try:
            element = self.find_clickable(self.LOGIN_BUTTON)
            self._smart_click(element); return
        except:
            pass
        element = self._find_clickable_first(self.LOGIN_BUTTON_FALLBACK)
        if element:
            self._smart_click(element)
    
    def _smart_click(self, element):
        try:
            self.driver.execute_script("arguments[0].scrollIntoView({behavior: 'auto', block: 'center'});", element)
            time.sleep(0.3)
        except:
            pass
        try:
            element.click(); return
        except:
            pass
        self.driver.execute_script("arguments[0].click();", element)
    
    def login(self, username, password):
        self.enter_username(username)
        self.enter_password(password)
        self.click_login_button()
        time.sleep(2)
    
    def is_login_success(self, expected_urls=None):
        if expected_urls is None:
            expected_urls = ["/dashboard/", "/admin_page/dashboard/", "/driver/dashboard/", "/home/", "/homepage/"]
        current_url = self.driver.current_url.lower()
        if "/login/" not in current_url and "login" not in current_url:
            return True
        return any(url.lower() in current_url for url in expected_urls)
    
    def get_error(self):
        try:
            toast = self.find_visible(self.TOAST_MESSAGE, timeout=3)
            text = toast.text.lower()
            if "error" in text or "invalid" in text or "failed" in text:
                return toast.text.strip()
        except:
            pass
        return None
    
    def get_toast_message(self):
        try:
            return self.find_visible(self.TOAST_MESSAGE, timeout=5).text.strip()
        except:
            return None