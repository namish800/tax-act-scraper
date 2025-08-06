"""
Simplified Income Tax Rules Scraper
Extracts: rule name, normalized rule name, description, rule URL

Based on the successful Beautiful Soup analysis that found onclick patterns.
"""

import requests
from bs4 import BeautifulSoup
import pandas as pd
import json
import re
import time

def normalize_rule_name(name):
    """Normalize rule names for consistency"""
    if not name:
        return ""
    
    # Remove extra whitespace and encode to handle unicode
    normalized = name.strip().encode('ascii', 'ignore').decode('ascii')
    
    # Clean up common patterns
    normalized = re.sub(r'\s+', ' ', normalized)  # Multiple spaces to single space
    normalized = re.sub(r'^\s*-\s*', '', normalized)  # Remove leading dash
    
    return normalized

def extract_rule_id_from_onclick(onclick_text):
    """Extract rule ID from onclick attribute like openRuleViewer('Rule', '103120000000009095', ...)"""
    if not onclick_text:
        return None
    
    # Look for the pattern openRuleViewer('Rule', 'ID', ...)
    match = re.search(r"openRuleViewer\s*\(\s*['\"]Rule['\"],\s*['\"]([^'\"]+)['\"]", onclick_text)
    if match:
        return match.group(1)
    
    return None

def scrape_rules_with_selenium():
    """Scrape rules using Selenium since requests are getting 503"""
    
    try:
        from selenium import webdriver
        from selenium.webdriver.common.by import By
        from selenium.webdriver.chrome.service import Service
        from selenium.common.exceptions import TimeoutException, ElementClickInterceptedException
        
        try:
            from webdriver_manager.chrome import ChromeDriverManager
            HAVE_WDM = True
        except Exception:
            HAVE_WDM = False
        
        # Setup Chrome
        options = webdriver.ChromeOptions()
        # Don't use headless mode - some sites block it
        # options.add_argument("--headless")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox") 
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        
        if HAVE_WDM:
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=options)
        else:
            driver = webdriver.Chrome(options=options)
        
        try:
            print(f"Loading page with Selenium...")
            driver.get("https://incometaxindia.gov.in/Pages/rules/income-tax-rules-1962.aspx")
            
            # Execute script to avoid detection
            driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            # Wait for page to load with better detection
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            
            print("Waiting for page content to load...")
            wait = WebDriverWait(driver, 30)
            
            # Wait for any content to appear
            try:
                wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
                time.sleep(15)  # Additional wait for JavaScript
            except:
                print("Timeout waiting for page elements")
                time.sleep(20)  # Fallback wait
            
            # Get page source and parse
            page_source = driver.page_source
            soup = BeautifulSoup(page_source, 'html.parser')
            
            # Debug: Check total onclick elements
            onclick_elements = soup.find_all(attrs={'onclick': True})
            print(f"Total onclick elements found: {len(onclick_elements)}")
            
            # Find all elements with onclick handlers containing openRuleViewer
            rule_elements = [elem for elem in onclick_elements 
                            if elem.get('onclick') and 'openruleviewer' in elem.get('onclick', '').lower()]
            
            print(f"Found {len(rule_elements)} rule elements")
            
            # Debug: If no rules found, check what onclick handlers we have
            if len(rule_elements) == 0:
                print("Debug: Checking onclick patterns...")
                for i, elem in enumerate(onclick_elements[:5]):
                    onclick = elem.get('onclick', '')
                    if onclick:
                        print(f"  Example onclick {i+1}: {onclick[:100]}...")
                
                # Also check page source length
                print(f"Page source length: {len(page_source)} characters")
                
                # Look for any rule-related text
                if 'rule' in page_source.lower():
                    print("Page contains 'rule' text - content is loading")
                else:
                    print("Page does NOT contain 'rule' text - content may not be loading")
            
            rules = []
            for i, element in enumerate(rule_elements):
                try:
                    onclick = element.get('onclick', '')
                    rule_id = extract_rule_id_from_onclick(onclick)
                    
                    # Extract rule text
                    rule_text = element.get_text().strip()
                    
                    if rule_id and rule_text:
                        # Split rule text into name and description
                        lines = [line.strip() for line in rule_text.split('\n') if line.strip()]
                        
                        if lines:
                            rule_name = lines[0]  # First line is usually "Rule - X"
                            description = ' '.join(lines[1:]) if len(lines) > 1 else ""
                            
                            rule_data = {
                                'rule_name': rule_name,
                                'normalized_rule_name': normalize_rule_name(rule_name),
                                'description': normalize_rule_name(description),
                                'rule_url': f"https://incometaxindia.gov.in/Rules/Income-Tax%20Rules/{rule_id}.htm",
                                'rule_id': rule_id,
                                'page_number': 1
                            }
                            
                            rules.append(rule_data)
                            print(f"  Rule {i+1}: {rule_name}")
                
                except Exception as e:
                    print(f"  Error processing rule element {i+1}: {e}")
                    continue
            
            return rules
            
        finally:
            driver.quit()
            
    except Exception as e:
        print(f"Selenium error: {e}")
        return []

def scrape_all_rules():
    """Main scraping function"""
    
    print("=== SIMPLIFIED INCOME TAX RULES SCRAPER ===\n")
    
    # Use Selenium since requests are getting 503 errors
    print("Using Selenium to scrape rules...")
    first_page_rules = scrape_rules_with_selenium()
    
    if not first_page_rules:
        print("No rules found on first page. Exiting.")
        return []
    
    all_rules = first_page_rules
    print(f"Successfully extracted {len(first_page_rules)} rules from page 1")
    
    # Now try to get more pages using Selenium for pagination
    print(f"\nExpanding to get all pages using Selenium for navigation...")
    
    # Try to get more rules using Selenium to handle pagination
    try:
        from selenium import webdriver
        from selenium.webdriver.common.by import By
        from selenium.webdriver.chrome.service import Service
        from selenium.common.exceptions import TimeoutException, ElementClickInterceptedException
        
        try:
            from webdriver_manager.chrome import ChromeDriverManager
            HAVE_WDM = True
        except Exception:
            HAVE_WDM = False
        
        # Setup Chrome for pagination
        options = webdriver.ChromeOptions()
        options.add_argument("--headless")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox") 
        options.add_argument("--disable-dev-shm-usage")
        
        if HAVE_WDM:
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=options)
        else:
            driver = webdriver.Chrome(options=options)
        
        try:
            driver.get("https://incometaxindia.gov.in/Pages/rules/income-tax-rules-1962.aspx")
            time.sleep(10)  # Wait for page to load
            
            # Try to get up to 10 pages for testing
            max_pages = 52
            current_page = 1  # Start from page 2 since we have page 1
            
            while current_page <= max_pages:
                try:
                    print(f"Attempting to navigate to page {current_page}...")
                    
                    # Look for page link
                    page_link = driver.find_element(By.XPATH, f"//a[text()='{current_page}']")
                    driver.execute_script("arguments[0].scrollIntoView(true);", page_link)
                    time.sleep(1)
                    
                    try:
                        page_link.click()
                    except ElementClickInterceptedException:
                        driver.execute_script("arguments[0].click();", page_link)
                    
                    time.sleep(5)  # Wait for page to load
                    
                    # Now scrape this page using BeautifulSoup on the current page source
                    page_source = driver.page_source
                    soup = BeautifulSoup(page_source, 'html.parser')
                    
                    onclick_elements = soup.find_all(attrs={'onclick': True})
                    rule_elements = [elem for elem in onclick_elements 
                                    if elem.get('onclick') and 'openruleviewer' in elem.get('onclick', '').lower()]
                    
                    print(f"Found {len(rule_elements)} rule elements on page {current_page}")
                    
                    page_rules = []
                    for element in rule_elements:
                        try:
                            onclick = element.get('onclick', '')
                            rule_id = extract_rule_id_from_onclick(onclick)
                            rule_text = element.get_text().strip()
                            
                            if rule_id and rule_text:
                                lines = [line.strip() for line in rule_text.split('\n') if line.strip()]
                                
                                if lines:
                                    rule_name = lines[0]
                                    description = ' '.join(lines[1:]) if len(lines) > 1 else ""
                                    
                                    rule_data = {
                                        'rule_name': rule_name,
                                        'normalized_rule_name': normalize_rule_name(rule_name),
                                        'description': normalize_rule_name(description),
                                        'rule_url': f"https://incometaxindia.gov.in/Rules/Income-Tax%20Rules/{rule_id}.htm",
                                        'rule_id': rule_id,
                                        'page_number': current_page
                                    }
                                    
                                    page_rules.append(rule_data)
                        except Exception as e:
                            continue
                    
                    all_rules.extend(page_rules)
                    print(f"Added {len(page_rules)} rules from page {current_page}")
                    current_page += 1
                    
                except Exception as e:
                    print(f"Could not navigate to page {current_page}: {e}")
                    break
        
        finally:
            driver.quit()
            
    except Exception as e:
        print(f"Selenium expansion failed: {e}")
        print("Continuing with rules from first page only...")
    
    print(f"Total rules extracted: {len(all_rules)}")
    
    # Save to both Excel and JSON
    if all_rules:
        print(f"\nSaving {len(all_rules)} rules to Excel and JSON...")
        
        # Create DataFrame
        df = pd.DataFrame(all_rules)
        
        # Reorder columns
        column_order = ['rule_name', 'normalized_rule_name', 'description', 'rule_url', 'rule_id', 'page_number']
        df = df[[col for col in column_order if col in df.columns]]
        
        # Save to Excel
        excel_file = 'D:/work/AI/ita/output/excel/income_tax_rules.xlsx'
        df.to_excel(excel_file, index=False, sheet_name='Rules')
        print(f"Excel saved to: {excel_file}")
        
        # Save to JSON
        json_file = 'D:/work/AI/ita/output/data/income_tax_rules.json'
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(all_rules, f, indent=2, ensure_ascii=False)
        print(f"JSON saved to: {json_file}")
        
        # Print summary
        print(f"\n=== SUMMARY ===")
        print(f"Total rules processed: {len(df)}")
        print(f"Unique rule IDs: {df['rule_id'].nunique()}")
        print(f"Pages processed: {df['page_number'].nunique()}")
        print(f"Sample rules:")
        for i, rule in enumerate(all_rules[:3]):
            print(f"  {i+1}. {rule['rule_name']} -> {rule['rule_url']}")
            if rule['description']:
                print(f"     Description: {rule['description'][:60]}...")
    
    return all_rules

if __name__ == "__main__":
    rules = scrape_all_rules()
    print(f"\nCompleted. Total rules: {len(rules)}")