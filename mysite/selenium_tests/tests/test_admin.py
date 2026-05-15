import pytest
from pages.login_page import LoginPage
import time

class TestAdmin:
    """Test admin dashboard functionality"""
    
    @pytest.fixture(autouse=True)
    def setup(self, setup):
        """Setup test fixtures"""
        self.driver = setup['driver']
        self.base_url = setup['base_url']
        self.login_page = LoginPage(self.driver, self.base_url)
        
        # Login as admin
        self.login_page.open_login_page()
        self.login_page.login("admin@test.com", "AdminPass123!")
        time.sleep(2)
    
    def test_admin_dashboard_access(self):
        """Test admin can access dashboard"""
        assert "/admin_page/dashboard/" in self.driver.current_url or "/dashboard/" in self.driver.current_url
    
    def test_view_users(self):
        """Test admin can view users"""
        self.driver.get(f"{self.base_url}/admin_page/users/")
        time.sleep(2)
        
        assert "/admin_page/users/" in self.driver.current_url
    
    def test_view_fleet(self):
        """Test admin can view fleet"""
        self.driver.get(f"{self.base_url}/admin_page/fleet/")
        time.sleep(2)
        
        assert "/admin_page/fleet/" in self.driver.current_url