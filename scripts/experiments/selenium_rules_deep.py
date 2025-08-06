"""
Deep dive into rules page with Selenium to find the actual content after dynamic loading
"""

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
import time
import re

try:
    from webdriver_manager.chrome import ChromeDriverManager
    HAVE_WDM = True
except:
    HAVE_WDM = False

def deep_selenium_analysis():
    url = "https://incometaxindia.gov.in/Pages/rules/income-tax-rules-1962.aspx"
    
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
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
        print("=== DEEP SELENIUM RULES ANALYSIS ===\n")
        
        driver.get(url)
        wait = WebDriverWait(driver, 30)
        
        print("1. WAITING FOR DYNAMIC CONTENT...")
        time.sleep(10)  # Give plenty of time for JS to load
        
        # 2. Check the actual page content
        print("2. PAGE CONTENT ANALYSIS:")
        page_source = driver.page_source
        print(f"  Page source length: {len(page_source)}")
        
        # Look for rule patterns in the loaded page
        rule_patterns = [
            r'Rule\s*[-\s]*\d+[A-Z]*',
            r'onclick.*rule',
            r'href.*rule',
            r'PrintRule',
            r'ViewRule',
            r'OpenRule'
        ]
        
        for pattern in rule_patterns:
            matches = re.findall(pattern, page_source, re.IGNORECASE)
            if matches:
                print(f"  Pattern '{pattern}': {len(matches)} matches")
                for match in matches[:3]:
                    print(f"    {match}")
        
        print()
        
        # 3. Look for all clickable elements
        print("3. CLICKABLE ELEMENTS ANALYSIS:")
        clickable_selectors = [
            "//a[@href]",
            "//button", 
            "//input[@type='button']",
            "//*[@onclick]",
            "//li[contains(@class, 'ui-li')]"
        ]
        
        for selector in clickable_selectors:
            try:
                elements = driver.find_elements(By.XPATH, selector)
                if elements:
                    print(f"  {selector}: {len(elements)} elements")
                    
                    # Look for rule-related ones
                    rule_elements = []
                    for elem in elements:
                        text = elem.text.strip()
                        onclick = elem.get_attribute('onclick') or ''
                        href = elem.get_attribute('href') or ''
                        
                        if any('rule' in x.lower() for x in [text, onclick, href]):
                            rule_elements.append({
                                'text': text[:50] if text else '',
                                'onclick': onclick[:50] if onclick else '',
                                'href': href[:50] if href else ''
                            })
                    
                    if rule_elements:
                        print(f"    {len(rule_elements)} rule-related elements:")
                        for i, elem in enumerate(rule_elements[:3]):
                            print(f"      {i+1}. Text: '{elem['text']}'")
                            if elem['onclick']:
                                print(f"          OnClick: {elem['onclick']}...")
                            if elem['href']:
                                print(f"          Href: {elem['href']}...")
                        
            except Exception as e:
                print(f"  Error with {selector}: {e}")
        
        print()
        
        # 4. Try to find specific rule content areas
        print("4. CONTENT AREA ANALYSIS:")
        content_selectors = [
            "//div[@id='content']",
            "//div[contains(@class, 'content')]",
            "//main",
            "//section",
            "//div[contains(@id, 'rule')]",
            "//div[contains(@class, 'rule')]"
        ]
        
        for selector in content_selectors:
            try:
                elements = driver.find_elements(By.XPATH, selector)
                if elements:
                    print(f"  {selector}: {len(elements)} elements")
                    for i, elem in enumerate(elements[:2]):
                        text = elem.text.strip()
                        if text and 'rule' in text.lower():
                            print(f"    Element {i+1}: {text[:100]}...")
            except Exception as e:
                print(f"  Error with {selector}: {e}")
        
        print()
        
        # 5. Save the actual loaded HTML for analysis
        print("5. SAVING LOADED HTML:")
        with open('D:\\work\\AI\\ita\\scripts\\experiments\\rules_loaded.html', 'w', encoding='utf-8') as f:
            f.write(page_source)
        print("  Saved loaded HTML to rules_loaded.html")
        
        # 6. Look for any data attributes or hidden content
        print("6. HIDDEN/DATA ATTRIBUTE ANALYSIS:")
        data_elements = driver.find_elements(By.XPATH, "//*[@data-*]")
        if data_elements:
            print(f"  Found {len(data_elements)} elements with data attributes")
            
        hidden_elements = driver.find_elements(By.XPATH, "//*[@style='display:none' or @style='display: none']")
        if hidden_elements:
            print(f"  Found {len(hidden_elements)} hidden elements")
            for i, elem in enumerate(hidden_elements[:3]):
                text = elem.text.strip()
                if text and 'rule' in text.lower():
                    print(f"    Hidden {i+1}: {text[:50]}...")
        
    finally:
        driver.quit()

if __name__ == "__main__":
    deep_selenium_analysis()