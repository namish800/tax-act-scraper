"""
Use Selenium to explore the Income Tax Rules page structure since it might be dynamic.
"""

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import TimeoutException
import time
import re

try:
    from webdriver_manager.chrome import ChromeDriverManager
    HAVE_WDM = True
except Exception:
    HAVE_WDM = False

def explore_rules_with_selenium():
    url = "https://incometaxindia.gov.in/Pages/rules/income-tax-rules-1962.aspx"
    
    # Setup Chrome options
    options = webdriver.ChromeOptions()
    # options.add_argument("--headless")  # Keep visible for now
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    
    if HAVE_WDM:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
    else:
        driver = webdriver.Chrome(options=options)
    
    try:
        print("=== SELENIUM EXPLORATION OF RULES PAGE ===\n")
        
        print("Loading rules page...")
        driver.get(url)
        
        # Wait for page to load
        wait = WebDriverWait(driver, 30)
        time.sleep(5)  # Give extra time for dynamic content
        
        # 1. Look for pagination info
        print("1. PAGINATION ANALYSIS:")
        try:
            # Look for pagination text
            pagination_elements = driver.find_elements(By.XPATH, "//*[contains(text(), 'Record') or contains(text(), 'Page')]")
            for elem in pagination_elements[:3]:
                text = elem.text.strip()
                if text and ('record' in text.lower() or 'page' in text.lower()):
                    print(f"  {text}")
        except Exception as e:
            print(f"  Error finding pagination: {e}")
        
        # Look for numbered page links
        try:
            page_links = driver.find_elements(By.XPATH, "//a[text()=1 or text()=2 or text()=3 or text()=4 or text()=5]")
            if page_links:
                print(f"  Found {len(page_links)} page number links")
        except Exception as e:
            print(f"  Error finding page links: {e}")
        
        print()
        
        # 2. Look for rule items/cards
        print("2. RULE ITEMS ANALYSIS:")
        
        # Try different selectors for rule containers
        rule_selectors = [
            "//li[contains(@class, 'ui-li')]",
            "//div[contains(@class, 'card')]", 
            "//tr[contains(., 'Rule')]",
            "//div[contains(text(), 'Rule -')]",
            "//a[contains(text(), 'Rule -')]"
        ]
        
        for selector in rule_selectors:
            try:
                elements = driver.find_elements(By.XPATH, selector)
                if elements:
                    print(f"  Found {len(elements)} elements with selector: {selector}")
                    
                    # Analyze first few elements
                    for i, elem in enumerate(elements[:3]):
                        text = elem.text.strip()[:100]
                        if text and 'rule' in text.lower():
                            print(f"    Element {i+1}: {text}...")
                            
                            # Look for print buttons or links within this element
                            try:
                                print_buttons = elem.find_elements(By.XPATH, ".//a[contains(@onclick, 'print') or contains(@onclick, 'Print')]")
                                if print_buttons:
                                    print(f"      Found {len(print_buttons)} print buttons")
                            except:
                                pass
                            
                        # Only show first selector that has results
                        break
            except Exception as e:
                print(f"  Error with selector {selector}: {e}")
        
        print()
        
        # 3. Look for specific rule patterns
        print("3. SPECIFIC RULE CONTENT:")
        
        try:
            # Look for elements containing "Rule - " followed by numbers
            rule_elements = driver.find_elements(By.XPATH, "//*[contains(text(), 'Rule - ')]")
            print(f"  Found {len(rule_elements)} elements containing 'Rule - '")
            
            for i, elem in enumerate(rule_elements[:10]):
                text = elem.text.strip()
                if text:
                    # Clean the text
                    clean_text = text.encode('ascii', 'ignore').decode('ascii')
                    print(f"    {i+1}. {clean_text[:100]}...")
                    
                    # Check if this element or its parent has links
                    try:
                        parent_links = elem.find_elements(By.XPATH, ".//a | ../a | ../../a")
                        if parent_links:
                            for link in parent_links[:1]:  # Just first link
                                href = link.get_attribute('href')
                                onclick = link.get_attribute('onclick')
                                if href and 'rule' in href.lower():
                                    print(f"      Link: {href}")
                                elif onclick and 'rule' in onclick.lower():
                                    print(f"      OnClick: {onclick[:50]}...")
                    except:
                        pass
        except Exception as e:
            print(f"  Error finding rule elements: {e}")
        
        print()
        
        # 4. Check page source for patterns
        print("4. PAGE SOURCE ANALYSIS:")
        page_source = driver.page_source
        print(f"  Page source length: {len(page_source)} characters")
        
        # Look for print section patterns like the sections page
        print_patterns = re.findall(r'PrintSection\([^)]+\)', page_source)
        if print_patterns:
            print(f"  Found {len(print_patterns)} PrintSection patterns")
            for pattern in print_patterns[:3]:
                print(f"    {pattern}")
        else:
            print("  No PrintSection patterns found")
        
        # Look for similar patterns with different names
        rule_patterns = re.findall(r'Print[Rr]ule\([^)]+\)', page_source)
        if rule_patterns:
            print(f"  Found {len(rule_patterns)} PrintRule patterns")
            for pattern in rule_patterns[:3]:
                print(f"    {pattern}")
        
        print()
        
        # 5. Wait for user inspection
        print("5. MANUAL INSPECTION:")
        print("Browser window is open for manual inspection.")
        print("Check the page structure and look for:")
        print("- How rules are displayed")
        print("- Print or view buttons")
        print("- Pagination elements")
        input("Press Enter to continue...")
        
    finally:
        driver.quit()

if __name__ == "__main__":
    explore_rules_with_selenium()