"""
Selenium-based paginated scraper that can handle ASP.NET postback pagination.
Extracts all sections from multiple pages with their related documents.
"""

import time
import json
import re
import pandas as pd
from typing import List, Dict, Any
import requests
from bs4 import BeautifulSoup

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import TimeoutException, NoSuchElementException

try:
    from webdriver_manager.chrome import ChromeDriverManager
    HAVE_WDM = True
except Exception:
    HAVE_WDM = False

def normalize_section_name(raw: str) -> str:
    """Normalize a section heading into a lowercase identifier."""
    raw = raw.strip()
    match = re.search(r"Section\s*[-:]*\s*(.+)", raw, re.IGNORECASE)
    identifier = match.group(1) if match else raw
    identifier = re.sub(r"\s+", "", identifier)
    return f"section_{identifier.lower()}"

def extract_section_id_from_url(section_url: str) -> str:
    """Extract the section ID from a section URL."""
    match = re.search(r'/(\d+)\.htm', section_url)
    return match.group(1) if match else ""

def get_related_documents_html(section_id: str) -> str:
    """Fetch related documents HTML for a given section ID."""
    if not section_id:
        return ""
        
    url = "https://incometaxindia.gov.in/_vti_bin/taxmann.iti.webservices/DataWebService.svc/GetRelatedDocuments"
    
    params = {
        'grp': 'Act',
        'searchText': section_id,
        'isCMSID': 'true'
    }
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'application/json, text/javascript, */*; q=0.01',
        'Accept-Language': 'en-US,en;q=0.9',
        'Referer': 'https://incometaxindia.gov.in/Pages/acts/income-tax-act.aspx'
    }
    
    try:
        response = requests.get(url, params=params, headers=headers, timeout=30)
        response.raise_for_status()
        data = response.json()
        return data if isinstance(data, str) else str(data)
    except Exception as e:
        return ""

def parse_related_documents(html_content: str) -> Dict[str, List[Dict]]:
    """Parse HTML content and extract structured information about related documents."""
    if not html_content:
        return {
            'rules': [],
            'forms': [],
            'notifications': [],
            'circulars': [],
            'faqs': [],
            'others': []
        }
    
    soup = BeautifulSoup(html_content, 'html.parser')
    result = {
        'rules': [],
        'forms': [],
        'notifications': [],
        'circulars': [],
        'faqs': [],
        'others': []
    }
    
    # Find all links in the content
    links = soup.find_all('a', href=True)
    
    for link in links:
        href = link.get('href', '')
        text = link.get_text().strip()
        
        if not text or len(text) < 5 or 'closePopup' in href.lower():
            continue
        
        # Clean up text to handle Unicode issues
        text = text.encode('ascii', 'ignore').decode('ascii')
        
        # Handle JavaScript URLs
        if href.startswith('javascript:'):
            js_url_match = re.search(r"'([^']+)'", href)
            if js_url_match:
                href = js_url_match.group(1)
            elif 'void(0)' in href:
                href = ''
        
        # Get description from parent context
        parent = link.find_parent(['li', 'td', 'div'])
        description = ''
        if parent:
            parent_text = parent.get_text().strip()
            parent_text = parent_text.encode('ascii', 'ignore').decode('ascii')
            if len(parent_text) > len(text):
                description = parent_text.replace(text, '').strip()
                description = re.sub(r'\s+', ' ', description)
        
        document_info = {
            'title': text,
            'url': href,
            'description': description
        }
        
        # Categorize the document
        text_lower = text.lower()
        
        if 'rule' in text_lower and href:
            result['rules'].append(document_info)
        elif 'form' in text_lower and href:
            result['forms'].append(document_info)
        elif 'notification' in text_lower and href:
            result['notifications'].append(document_info)
        elif 'circular' in text_lower and href:
            result['circulars'].append(document_info)
        elif not href or 'void(0)' in href:
            result['faqs'].append(document_info)
        else:
            result['others'].append(document_info)
    
    return result

def extract_sections_from_current_page(driver: webdriver.Chrome, page_num: int) -> List[Dict[str, Any]]:
    """Extract sections from the currently loaded page."""
    
    wait = WebDriverWait(driver, 10)
    page_results = []
    
    try:
        # Wait for sections to load
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "li.ui-li")))
        
        # Find all print buttons on this page
        print_buttons = driver.find_elements(By.XPATH, "//a[contains(@onclick, 'PrintSection')]")
        
        print(f"    Found {len(print_buttons)} sections on page {page_num}")
        
        for i, button in enumerate(print_buttons, 1):
            onclick = button.get_attribute('onclick')
            
            # Extract URL and section name from onclick attribute
            match = re.search(r"PrintSection\('([^']+)',\s*'[^']*',\s*'([^']+)'\)", onclick)
            
            if match:
                section_url = match.group(1)
                section_title = match.group(2)
                normalized_name = normalize_section_name(section_title)
                
                # Extract section ID from URL
                section_id = extract_section_id_from_url(section_url)
                
                # Find section description
                section_description = ""
                try:
                    # Navigate up to find the parent li element
                    parent_li = button.find_element(By.XPATH, "./ancestor::li[contains(@class, 'ui-li')]")
                    desc_element = parent_li.find_element(By.CSS_SELECTOR, "p.dt-text-info-p")
                    section_description = desc_element.text.strip()
                    section_description = section_description.encode('ascii', 'ignore').decode('ascii')
                except NoSuchElementException:
                    pass
                
                print(f"      Processing {normalized_name} ({i}/{len(print_buttons)})...")
                
                # Get related documents
                related_docs_html = get_related_documents_html(section_id)
                related_docs = parse_related_documents(related_docs_html)
                
                # Count related documents
                doc_counts = {category: len(docs) for category, docs in related_docs.items()}
                total_related = sum(doc_counts.values())
                
                section_info = {
                    'section_name': normalized_name,
                    'section_title': section_title,
                    'section_description': section_description,
                    'section_url': section_url,
                    'section_id': section_id,
                    'page_number': page_num,
                    'total_related_documents': total_related,
                    'rules_count': doc_counts['rules'],
                    'forms_count': doc_counts['forms'],
                    'notifications_count': doc_counts['notifications'],
                    'circulars_count': doc_counts['circulars'],
                    'faqs_count': doc_counts['faqs'],
                    'others_count': doc_counts['others'],
                    'related_documents': related_docs
                }
                
                page_results.append(section_info)
                
                if total_related > 0:
                    print(f"        Found {total_related} related documents")
                
                # Small delay between sections
                time.sleep(0.3)
        
        return page_results
        
    except TimeoutException:
        print(f"    Timeout waiting for sections on page {page_num}")
        return []
    except Exception as e:
        print(f"    Error processing page {page_num}: {e}")
        return []

def navigate_to_page(driver: webdriver.Chrome, page_num: int) -> bool:
    """Navigate to a specific page using pagination."""
    
    if page_num == 1:
        return True  # Already on page 1
    
    wait = WebDriverWait(driver, 15)
    
    try:
        # Scroll to the bottom of the page to make pagination visible
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)
        
        # Look for page number links with more specific selectors
        page_link_selectors = [
            f"//a[text()='{page_num}' and not(@disabled)]",
            f"//a[contains(@href, 'page') and text()='{page_num}']",
            f"//a[contains(text(), '{page_num}')]"
        ]
        
        page_link = None
        for selector in page_link_selectors:
            try:
                page_links = driver.find_elements(By.XPATH, selector)
                if page_links:
                    page_link = page_links[0]
                    break
            except:
                continue
        
        if page_link:
            # Scroll the element into view
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", page_link)
            time.sleep(1)
            
            # Try clicking with JavaScript first (more reliable)
            try:
                driver.execute_script("arguments[0].click();", page_link)
                print(f"    Clicked page {page_num} link using JavaScript")
            except:
                # Fallback to regular click
                try:
                    wait.until(EC.element_to_be_clickable(page_link))
                    page_link.click()
                    print(f"    Clicked page {page_num} link using regular click")
                except:
                    print(f"    Could not click page {page_num} link")
                    return False
            
            # Wait for page to load
            print(f"    Waiting for page {page_num} to load...")
            time.sleep(5)
            
            # Verify we're on the correct page by checking if sections loaded
            try:
                wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "li.ui-li")))
                
                # Additional verification - check if pagination text updated
                try:
                    pagination_elements = driver.find_elements(By.XPATH, f"//*[contains(text(), 'Page [{page_num} of')]")
                    if pagination_elements:
                        print(f"    Successfully verified page {page_num}")
                        return True
                except:
                    pass
                
                # Even if we can't verify the exact page number, if sections loaded, likely successful
                sections = driver.find_elements(By.CSS_SELECTOR, "li.ui-li")
                if sections:
                    print(f"    Page {page_num} loaded (found {len(sections)} sections)")
                    return True
                else:
                    print(f"    No sections found on page {page_num}")
                    return False
                    
            except TimeoutException:
                print(f"    Timeout waiting for sections on page {page_num}")
                return False
                
        else:
            print(f"    Page {page_num} link not found in pagination")
            
            # Try alternative approach - look for "Next" button if we're on consecutive pages
            if page_num == 2:
                try:
                    next_buttons = driver.find_elements(By.XPATH, "//a[contains(text(), 'Next') or contains(@title, 'Next') or contains(@aria-label, 'Next')]")
                    if next_buttons:
                        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", next_buttons[0])
                        time.sleep(1)
                        driver.execute_script("arguments[0].click();", next_buttons[0])
                        print(f"    Used 'Next' button to navigate to page {page_num}")
                        time.sleep(5)
                        return True
                except:
                    pass
            
            return False
            
    except Exception as e:
        print(f"    Error navigating to page {page_num}: {e}")
        return False

def extract_all_sections_selenium(max_pages: int = 3) -> List[Dict[str, Any]]:
    """Extract sections from multiple pages using Selenium."""
    
    url = "https://incometaxindia.gov.in/Pages/acts/income-tax-act.aspx"
    
    # Setup Chrome options
    options = webdriver.ChromeOptions()
    # options.add_argument("--headless")  # Run in background
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36')
    
    # Initialize driver
    if HAVE_WDM:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
    else:
        driver = webdriver.Chrome(options=options)
    
    all_sections = []
    
    try:
        print(f"Loading main page...")
        driver.get(url)
        
        # Wait for page to load
        wait = WebDriverWait(driver, 30)
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "li.ui-li")))
        
        # Get total pages from pagination info
        try:
            pagination_element = driver.find_element(By.XPATH, "//*[contains(text(), 'Page [')]")
            pagination_text = pagination_element.text
            match = re.search(r'of\s+(\d+)', pagination_text)
            total_pages = int(match.group(1)) if match else 1
            print(f"Found {total_pages} total pages")
        except:
            total_pages = 94  # Default based on web analysis
            print(f"Using default total pages: {total_pages}")
        
        # Limit pages for testing
        max_pages = min(max_pages, total_pages)
        print(f"Processing first {max_pages} pages")
        
        # Process each page
        for page_num in range(1, max_pages + 1):
            print(f"\nProcessing page {page_num}/{max_pages}...")
            
            if page_num > 1:
                success = navigate_to_page(driver, page_num)
                if not success:
                    print(f"    Failed to navigate to page {page_num}, stopping")
                    break
            
            # Extract sections from current page
            page_sections = extract_sections_from_current_page(driver, page_num)
            all_sections.extend(page_sections)
            
            print(f"    Extracted {len(page_sections)} sections from page {page_num}")
            print(f"    Total sections so far: {len(all_sections)}")
            
            # Longer delay between pages
            if page_num < max_pages:
                time.sleep(2)
        
    finally:
        driver.quit()
    
    return all_sections

def save_to_excel(sections_data: List[Dict[str, Any]], filename: str = "selenium_income_tax_sections.xlsx"):
    """Save data to Excel with multiple sheets."""
    
    print(f"Saving data to {filename}...")
    
    # Create main sections sheet
    sections_df_data = []
    all_rules = []
    all_forms = []
    all_faqs = []
    
    for section in sections_data:
        sections_df_data.append({
            'section_name': section['section_name'],
            'section_title': section['section_title'],
            'section_description': section['section_description'],
            'section_url': section['section_url'],
            'section_id': section['section_id'],
            'page_number': section['page_number'],
            'total_related_documents': section['total_related_documents'],
            'rules_count': section['rules_count'],
            'forms_count': section['forms_count'],
            'faqs_count': section['faqs_count']
        })
        
        # Collect related documents
        for rule in section['related_documents']['rules']:
            all_rules.append({
                'section_name': section['section_name'],
                'section_title': section['section_title'],
                'page_number': section['page_number'],
                'rule_title': rule['title'],
                'rule_url': rule['url']
            })
        
        for form in section['related_documents']['forms']:
            all_forms.append({
                'section_name': section['section_name'],
                'section_title': section['section_title'],
                'page_number': section['page_number'],
                'form_title': form['title'],
                'form_url': form['url']
            })
        
        for faq in section['related_documents']['faqs']:
            all_faqs.append({
                'section_name': section['section_name'],
                'section_title': section['section_title'],
                'page_number': section['page_number'],
                'question': faq['title'],
                'answer': faq['description']
            })
    
    # Save to Excel
    sections_df = pd.DataFrame(sections_df_data)
    
    with pd.ExcelWriter(filename, engine='openpyxl') as writer:
        sections_df.to_excel(writer, sheet_name='Sections', index=False)
        
        if all_rules:
            pd.DataFrame(all_rules).to_excel(writer, sheet_name='Rules', index=False)
        if all_forms:
            pd.DataFrame(all_forms).to_excel(writer, sheet_name='Forms', index=False)
        if all_faqs:
            pd.DataFrame(all_faqs).to_excel(writer, sheet_name='FAQs', index=False)
    
    print(f"Data saved to {filename}")
    print(f"Summary: {len(sections_data)} sections, {len(all_rules)} rules, {len(all_forms)} forms, {len(all_faqs)} FAQs")

def main():
    """Main function to run the Selenium-based scraper."""
    print("Selenium-based Income Tax Act scraper with pagination")
    print("Testing with first 3 pages...")
    print()
    
    try:
        # Extract sections from first 3 pages
        sections_data = extract_all_sections_selenium(max_pages=94)
        
        if sections_data:
            # Save to Excel
            save_to_excel(sections_data)
            
            # Also save as JSON
            with open('selenium_income_tax_data.json', 'w', encoding='utf-8') as f:
                json.dump(sections_data, f, indent=2, ensure_ascii=False)
            
            print(f"Successfully processed {len(sections_data)} sections")
            print("Data saved to selenium_income_tax_sections.xlsx")
            print("Raw data saved to selenium_income_tax_data.json")
        else:
            print("No sections were extracted")
            
    except Exception as e:
        print(f"Error during scraping: {e}")
        raise

if __name__ == "__main__":
    main()