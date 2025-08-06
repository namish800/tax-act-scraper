"""
Script to check if there are API endpoints or data sources 
for related rules and forms information.
"""

import requests
from bs4 import BeautifulSoup
import re

def check_for_api_endpoints():
    url = "https://incometaxindia.gov.in/Pages/acts/income-tax-act.aspx"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    response = requests.get(url, headers=headers, timeout=30)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    print("=== CHECKING FOR API ENDPOINTS AND DATA SOURCES ===\n")
    
    # Look for URLs in JavaScript that might be API endpoints
    scripts = soup.find_all('script')
    potential_urls = []
    
    for script in scripts:
        if script.string:
            # Look for URLs in JavaScript
            urls = re.findall(r'https?://[^\s"\'>]+', script.string)
            if urls:
                potential_urls.extend(urls)
            
            # Look for relative paths that might be API endpoints
            relative_paths = re.findall(r'["\']([/][^"\'>\s]+\.aspx?[^"\'>\s]*)["\']', script.string)
            if relative_paths:
                potential_urls.extend([f"https://incometaxindia.gov.in{path}" for path in relative_paths])
    
    # Remove duplicates and filter relevant ones
    unique_urls = list(set(potential_urls))
    relevant_urls = [url for url in unique_urls if any(keyword in url.lower() 
                    for keyword in ['rule', 'form', 'content', 'search', 'api', 'service'])]
    
    print(f"Found {len(unique_urls)} unique URLs in JavaScript")
    print(f"Found {len(relevant_urls)} potentially relevant URLs:")
    
    for url in relevant_urls[:10]:  # Show first 10
        print(f"  {url}")
    
    print("\n" + "="*50)
    
    # Check if there are any form elements that might submit requests for rules/forms
    forms = soup.find_all('form')
    print(f"Found {len(forms)} form elements")
    
    for i, form in enumerate(forms):
        action = form.get('action', '')
        method = form.get('method', 'GET')
        if action:
            print(f"Form {i+1}: {method} -> {action}")
    
    print("\n" + "="*50)
    
    # Let's try to understand the section structure better
    # Maybe the rules and forms are embedded in the page already but hidden
    print("EXAMINING SECTION STRUCTURE FOR EMBEDDED RULES/FORMS:")
    
    # Find all li elements with ui-li class (these contain sections)
    section_lis = soup.find_all('li', class_='ui-li')
    print(f"Found {len(section_lis)} section containers")
    
    # Check if any contain additional hidden content
    for i, li in enumerate(section_lis[:3]):  # Check first 3
        print(f"\nSection {i+1}:")
        
        # Get section title
        title_p = li.find('p', class_='dt-text-info-p')
        if title_p:
            print(f"  Title: {title_p.get_text().strip()}")
        
        # Look for any additional elements that might contain rules/forms
        all_text_elements = li.find_all(text=True)
        text_content = ' '.join([t.strip() for t in all_text_elements if t.strip()])
        
        # Check if rules/forms keywords appear in the text
        if any(keyword in text_content.lower() for keyword in ['rule', 'form', 'notification', 'circular']):
            print(f"  Contains rule/form keywords: {text_content[:200]}...")
        
        # Look for any nested div elements that might expand
        nested_divs = li.find_all('div')
        if nested_divs:
            print(f"  Contains {len(nested_divs)} nested div elements")
            for j, div in enumerate(nested_divs):
                if div.get_text().strip() and len(div.get_text().strip()) > 50:
                    print(f"    Div {j+1}: {div.get_text().strip()[:100]}...")

if __name__ == "__main__":
    check_for_api_endpoints()