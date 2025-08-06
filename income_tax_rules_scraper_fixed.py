"""
Income Tax Rules Scraper - Fixed Single Driver Version
Follows the same structure as income_tax_scraper.py
"""

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import TimeoutException, ElementClickInterceptedException, NoSuchElementException
import pandas as pd
import json
import time
import re
from bs4 import BeautifulSoup

try:
    from webdriver_manager.chrome import ChromeDriverManager
    HAVE_WDM = True
except Exception:
    HAVE_WDM = False

# Configuration
TEST_MODE = True  # Set to False for all 52 pages
MAX_TEST_PAGES = 10  # Only used when TEST_MODE is True
TOTAL_PAGES = 52

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

def extract_rules_from_current_page(driver, page_num):
    """Extract rules from the current page using BeautifulSoup on page source"""
    
    try:
        # Get page source and parse with BeautifulSoup
        page_source = driver.page_source
        soup = BeautifulSoup(page_source, 'html.parser')
        
        # Find all elements with onclick handlers containing openRuleViewer
        onclick_elements = soup.find_all(attrs={'onclick': True})
        rule_elements = [elem for elem in onclick_elements 
                        if elem.get('onclick') and 'openruleviewer' in elem.get('onclick', '').lower()]
        
        print(f"    Found {len(rule_elements)} rule elements on page {page_num}")
        
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
                            'page_number': page_num
                        }
                        
                        rules.append(rule_data)
                        print(f"      Rule {i+1}: {rule_name}")
            
            except Exception as e:
                print(f"      Error processing rule element {i+1}: {e}")
                continue
        
        return rules
        
    except Exception as e:
        print(f"    Error extracting rules from page {page_num}: {e}")
        return []

def navigate_to_page(driver, page_num):
    """Navigate to a specific page using pagination (same as income_tax_scraper.py)"""
    
    if page_num == 1:
        return True
    
    try:
        # Scroll to bottom to find pagination
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)
        
        # Look for page link
        page_link = None
        page_links = driver.find_elements(By.XPATH, f"//a[text()='{page_num}' and not(@disabled)]")
        if page_links:
            page_link = page_links[0]
        
        if page_link:
            # Scroll to element and click
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", page_link)
            time.sleep(1)
            
            driver.execute_script("arguments[0].click();", page_link)
            print(f"    Navigated to page {page_num}")
            time.sleep(5)  # Wait for page to load
            
            # Wait for content to appear
            wait = WebDriverWait(driver, 15)
            wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            return True
        else:
            print(f"    Page {page_num} link not found")
            return False
            
    except Exception as e:
        print(f"    Error navigating to page {page_num}: {e}")
        return False

def extract_all_rules(max_pages=None):
    """Main extraction function using single driver (same pattern as income_tax_scraper.py)"""
    
    if max_pages is None:
        max_pages = MAX_TEST_PAGES if TEST_MODE else TOTAL_PAGES
    
    base_url = "https://incometaxindia.gov.in/Pages/rules/income-tax-rules-1962.aspx"
    
    # Setup Chrome options (same as income_tax_scraper.py)
    options = webdriver.ChromeOptions()
    # Don't use headless mode - some sites block it
    # options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36')
    
    if HAVE_WDM:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
    else:
        driver = webdriver.Chrome(options=options)
    
    all_rules = []
    
    try:
        print("=== INCOME TAX RULES SCRAPER (SINGLE DRIVER) ===\n")
        
        if TEST_MODE:
            print(f"TEST MODE: Processing first {max_pages} pages")
        else:
            print(f"PRODUCTION MODE: Processing all {TOTAL_PAGES} pages")
        
        print(f"Expected total rules: ~{max_pages * 10}")
        print()
        
        # Load initial page
        print(f"Loading main page...")
        driver.get(base_url)
        
        # Wait for page to load
        wait = WebDriverWait(driver, 30)
        wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        
        # Execute script to avoid detection
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        # Wait additional time for JavaScript
        time.sleep(15)
        
        # Process each page
        for page_num in range(1, max_pages + 1):
            print(f"\n--- Processing page {page_num}/{max_pages} ---")
            
            # Navigate to page (if not page 1)
            if page_num > 1:
                success = navigate_to_page(driver, page_num)
                if not success:
                    print(f"Failed to navigate to page {page_num}, stopping")
                    break
            
            # Extract rules from current page
            page_rules = extract_rules_from_current_page(driver, page_num)
            all_rules.extend(page_rules)
            
            print(f"    Extracted {len(page_rules)} rules from page {page_num}")
            print(f"    Total rules so far: {len(all_rules)}")
            
            # Small delay before next page
            if page_num < max_pages:
                time.sleep(2)
        
    finally:
        driver.quit()
    
    print(f"\n=== SCRAPING COMPLETE ===")
    print(f"Total rules extracted: {len(all_rules)}")
    
    return all_rules

def save_rules_data(rules_data, base_filename="income_tax_rules"):
    """Save rules data to both Excel and JSON"""
    
    if not rules_data:
        print("No rules data to save")
        return
    
    print(f"\nSaving {len(rules_data)} rules to Excel and JSON...")
    
    # Create DataFrame
    df = pd.DataFrame(rules_data)
    
    # Reorder columns
    column_order = ['rule_name', 'normalized_rule_name', 'description', 'rule_url', 'rule_id', 'page_number']
    df = df[[col for col in column_order if col in df.columns]]
    
    # Save to Excel
    excel_file = f'D:/work/AI/ita/output/excel/{base_filename}.xlsx'
    df.to_excel(excel_file, index=False, sheet_name='Rules')
    print(f"Excel saved to: {excel_file}")
    
    # Save to JSON
    json_file = f'D:/work/AI/ita/output/data/{base_filename}.json'
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(rules_data, f, indent=2, ensure_ascii=False)
    print(f"JSON saved to: {json_file}")
    
    # Print summary
    print(f"\n=== SUMMARY STATISTICS ===")
    print(f"Total rules processed: {len(df)}")
    print(f"Unique rule IDs: {df['rule_id'].nunique()}")
    print(f"Pages successfully processed: {df['page_number'].nunique()}")
    print(f"Rules with descriptions: {sum(1 for desc in df['description'] if desc)}")
    
    print(f"\nSample rules:")
    for i, rule in enumerate(rules_data[:5]):
        print(f"  {i+1}. {rule['rule_name']} -> {rule['rule_url']}")
        if rule['description']:
            print(f"     Description: {rule['description'][:60]}...")

if __name__ == "__main__":
    rules = extract_all_rules(52)
    save_rules_data(rules)
    print(f"\nCompleted. Total rules: {len(rules)}")