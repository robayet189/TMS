#!/usr/bin/env python
"""
Quick debug script to inspect actual HTML selectors in your Easy Transport app.
Run this to see what name/id attributes your forms actually use.
"""
import os, sys, time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

def debug_page(url, title):
    print(f"\n{'='*60}")
    print(f"🔍 Debugging: {title}")
    print(f"URL: {url}")
    print('='*60)
    
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--window-size=1920,1080")
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    
    try:
        driver.get(url)
        wait = WebDriverWait(driver, 10)
        
        # Wait for body to load
        wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        time.sleep(2)  # Let JS render
        
        print(f"\n📋 Current URL: {driver.current_url}")
        
        # Print all inputs
        print(f"\n📝 Input fields ({len(driver.find_elements(By.TAG_NAME, 'input'))} found):")
        for inp in driver.find_elements(By.TAG_NAME, "input"):
            name = inp.get_attribute("name") or "-"
            id_attr = inp.get_attribute("id") or "-"
            type_attr = inp.get_attribute("type") or "text"
            placeholder = inp.get_attribute("placeholder") or "-"
            print(f"  • type='{type_attr}' name='{name}' id='{id_attr}' placeholder='{placeholder}'")
        
        # Print all buttons
        print(f"\n🔘 Buttons ({len(driver.find_elements(By.TAG_NAME, 'button'))} found):")
        for btn in driver.find_elements(By.TAG_NAME, "button"):
            text = btn.text.strip() or "-"
            btn_type = btn.get_attribute("type") or "-"
            btn_id = btn.get_attribute("id") or "-"
            btn_class = btn.get_attribute("class") or "-"
            print(f"  • text='{text}' type='{btn_type}' id='{btn_id}' class='{btn_class}'")
        
        # Print all forms
        print(f"\n📄 Forms ({len(driver.find_elements(By.TAG_NAME, 'form'))} found):")
        for form in driver.find_elements(By.TAG_NAME, "form"):
            action = form.get_attribute("action") or "-"
            method = form.get_attribute("method") or "get"
            form_id = form.get_attribute("id") or "-"
            print(f"  • id='{form_id}' action='{action}' method='{method}'")
            
            # Print inputs inside this form
            for inp in form.find_elements(By.TAG_NAME, "input"):
                name = inp.get_attribute("name") or "-"
                print(f"    └─ input name='{name}'")
        
        # Check for common Django patterns
        print(f"\n🔎 Checking for Django patterns:")
        csrf = driver.find_elements(By.NAME, "csrfmiddlewaretoken")
        print(f"  • CSRF token: {'✅ Found' if csrf else '❌ Not found'}")
        
        # Check for common field names
        common_fields = ["username", "email", "password", "full_name", "phone", "first_name", "last_name"]
        for field in common_fields:
            found = driver.find_elements(By.NAME, field)
            print(f"  • '{field}': {'✅ Found' if found else '❌ Not found'}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        driver.quit()

if __name__ == "__main__":
    BASE_URL = "http://127.0.0.1:8000"
    
    print("🚀 Easy Transport Selector Debug Tool")
    print(f"Target: {BASE_URL}")
    
    # Debug key pages
    debug_page(f"{BASE_URL}/login/", "Login Page")
    debug_page(f"{BASE_URL}/register/", "Registration Page")
    debug_page(f"{BASE_URL}/dashboard/", "Dashboard (requires login - may redirect)")
    debug_page(f"{BASE_URL}/schedule/", "Schedule Page")
    
    print(f"\n{'='*60}")
    print("✅ Debug complete! Use the output above to fix your test selectors.")
    print('='*60)