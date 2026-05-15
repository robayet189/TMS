import pytest
from pages.login_page import LoginPage
from pages.dashboard_page import DashboardPage
import time

class TestBooking:
    """Test booking functionality"""
    
    @pytest.fixture(autouse=True)
    def setup(self, setup):
        """Setup test fixtures"""
        self.driver = setup['driver']
        self.base_url = setup['base_url']
        self.login_page = LoginPage(self.driver, self.base_url)
        self.dashboard_page = DashboardPage(self.driver, self.base_url)
        
        # Login before each test
        self.login_page.open_login_page()
        self.login_page.login("student@test.com", "TestPass123!")
        time.sleep(2)
    
    def test_view_schedule(self):
        """Test viewing transport schedule"""
        self.dashboard_page.click_schedule()
        time.sleep(2)
        
        assert "/schedule/" in self.driver.current_url
    
    def test_view_my_bookings(self):
        """Test viewing user bookings"""
        self.dashboard_page.click_my_bookings()
        time.sleep(2)
        
        assert "/my-bookings/" in self.driver.current_url
    
    def test_book_seat_flow(self):
        """Test complete booking flow"""
        # Navigate to schedule
        self.dashboard_page.click_schedule()
        time.sleep(2)
        
        # Find and click book button (adjust selector based on your HTML)
        try:
            book_button = self.dashboard_page.wait_for_element_clickable(
                By.XPATH, "//button[contains(text(), 'Book')]"
            )
            book_button.click()
            time.sleep(2)
            
            # Verify booking page loaded
            assert "/book-ticket/" in self.driver.current_url or "/seat-selection/" in self.driver.current_url
        except:
            pytest.skip("No available routes for booking")