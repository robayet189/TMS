# selenium_tests/pages/base_page.py
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, ElementClickInterceptedException
import time

class BasePage:
    def __init__(self, driver, base_url):
        self.driver = driver
        # ✅ FIXED: Ensure base_url is never empty
        self.base_url = base_url if base_url and base_url.strip() else "http://127.0.0.1:8000"
        self.wait = WebDriverWait(driver, 10)
    
    def open(self, path):
        """Navigate to path with full URL"""
        base = self.base_url.rstrip('/')
        url_path = path if path.startswith('/') else f'/{path}'
        full_url = f"{base}{url_path}"
        
        if not full_url.startswith(('http://', 'https://')):
            full_url = f"http://{full_url}"
        
        self.driver.get(full_url)
        time.sleep(0.5)
    
    def find(self, locator, timeout=10):
        return WebDriverWait(self.driver, timeout).until(
            EC.presence_of_element_located(locator)
        )
    
    def find_clickable(self, locator, timeout=10):
        return WebDriverWait(self.driver, timeout).until(
            EC.element_to_be_clickable(locator)
        )
    
    def find_visible(self, locator, timeout=10):
        return WebDriverWait(self.driver, timeout).until(
            EC.visibility_of_element_located(locator)
        )
    
    def click(self, locator):
        element = self.find_clickable(locator)
        try:
            self.driver.execute_script("arguments[0].scrollIntoView({behavior: 'auto', block: 'center'});", element)
            time.sleep(0.3)
        except:
            pass
        try:
            element.click()
            return
        except ElementClickInterceptedException:
            pass
        try:
            self.driver.execute_script("arguments[0].click();", element)
            return
        except:
            pass
        from selenium.webdriver.common.action_chains import ActionChains
        actions = ActionChains(self.driver)
        actions.move_to_element(element).click().perform()
    
    def enter_text(self, locator, text):
        element = self.find(locator)
        element.clear()
        element.send_keys(text)
    
    def get_text(self, locator):
        return self.find(locator).text.strip()
    
    def is_visible(self, locator, timeout=5):
        try:
            self.find_visible(locator, timeout)
            return True
        except TimeoutException:
            return False
    
    def get_current_url(self):
        return self.driver.current_url
    
    def wait_for_url_contains(self, text, timeout=10):
        WebDriverWait(self.driver, timeout).until(EC.url_contains(text))