from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

class BasePage:
    """Base class for all page objects"""
    
    def __init__(self, driver, base_url):
        self.driver = driver
        self.base_url = base_url
        self.wait = WebDriverWait(driver, 10)
    
    def open_url(self, path):
        """Open URL path"""
        self.driver.get(f"{self.base_url}{path}")
    
    def find_element(self, by, value):
        """Find element"""
        return self.driver.find_element(by, value)
    
    def find_elements(self, by, value):
        """Find elements"""
        return self.driver.find_elements(by, value)
    
    def wait_for_element_visible(self, by, value, timeout=10):
        """Wait for element to be visible"""
        try:
            return WebDriverWait(self.driver, timeout).until(
                EC.visibility_of_element_located((by, value))
            )
        except TimeoutException:
            raise Exception(f"Element not found: {value}")
    
    def wait_for_element_clickable(self, by, value, timeout=10):
        """Wait for element to be clickable"""
        try:
            return WebDriverWait(self.driver, timeout).until(
                EC.element_to_be_clickable((by, value))
            )
        except TimeoutException:
            raise Exception(f"Element not clickable: {value}")
    
    def click_element(self, by, value):
        """Click element"""
        element = self.wait_for_element_clickable(by, value)
        element.click()
    
    def enter_text(self, by, value, text):
        """Enter text into input field"""
        element = self.wait_for_element_visible(by, value)
        element.clear()
        element.send_keys(text)
    
    def get_element_text(self, by, value):
        """Get element text"""
        element = self.wait_for_element_visible(by, value)
        return element.text
    
    def is_element_present(self, by, value):
        """Check if element is present"""
        try:
            self.driver.find_element(by, value)
            return True
        except:
            return False
    
    def get_current_url(self):
        """Get current URL"""
        return self.driver.current_url
    
    def take_screenshot(self, filename):
        """Take screenshot"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        screenshot_path = f"screenshots/{timestamp}_{filename}.png"
        self.driver.save_screenshot(screenshot_path)
        return screenshot_path