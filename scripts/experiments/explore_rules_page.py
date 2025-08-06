"""
Script to explore the Income Tax Rules page structure and understand
how to extract rule information.
"""

import requests
from bs4 import BeautifulSoup
import re

def explore_rules_page():
    url = "https://incometaxindia.gov.in/Pages/rules/income-tax-rules-1962.aspx"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    response = requests.get(url, headers=headers, timeout=30)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    print("=== INCOME TAX RULES PAGE STRUCTURE ANALYSIS ===\n")
    
    # 1. Look for pagination info
    print("1. PAGINATION ANALYSIS:")
    pagination_texts = soup.find_all(string=re.compile(r'\d+.*record|page.*of', re.IGNORECASE))
    for text in pagination_texts[:3]:
        clean_text = ' '.join(text.split())
        if clean_text.strip():
            print(f"  {clean_text}")
    
    # Look for pagination elements
    page_elements = soup.find_all('a', string=re.compile(r'^\d+$'))
    if page_elements:
        print(f"  Found {len(page_elements)} numbered page links")
        page_numbers = [int(elem.get_text()) for elem in page_elements if elem.get_text().isdigit()]
        if page_numbers:
            print(f"  Page range: {min(page_numbers)} to {max(page_numbers)}")
    
    print()
    
    # 2. Look for rule containers/cards
    print("2. RULE CONTAINER ANALYSIS:")
    
    # Try different selectors for rule containers
    container_selectors = [
        'div.card',
        'li.ui-li', 
        'div[class*="rule"]',
        'tr',
        'div[class*="item"]'
    ]
    
    for selector in container_selectors:
        elements = soup.select(selector)
        if elements:
            print(f"  Found {len(elements)} elements with selector: {selector}")
            
            # Analyze first few elements
            for i, elem in enumerate(elements[:3]):
                text_content = elem.get_text().strip()[:100]
                if 'rule' in text_content.lower():
                    print(f"    Element {i+1}: {text_content}...")
    
    print()
    
    # 3. Look for rule titles and patterns
    print("3. RULE TITLE PATTERNS:")
    
    # Look for text containing "Rule"
    rule_texts = soup.find_all(string=re.compile(r'Rule\s*[-\s]*\d+', re.IGNORECASE))
    for i, text in enumerate(rule_texts[:10]):
        clean_text = ' '.join(text.split())
        clean_text = clean_text.encode('ascii', 'ignore').decode('ascii')
        if clean_text.strip():
            print(f"  {i+1}. {clean_text}")
    
    print()
    
    # 4. Look for print buttons or links to full rules
    print("4. PRINT BUTTON/LINK ANALYSIS:")
    
    # Look for print-related elements
    print_elements = soup.find_all('a', {'onclick': lambda x: x and ('print' in x.lower() or 'rule' in x.lower())})
    print(f"  Found {len(print_elements)} potential print elements")
    
    for i, elem in enumerate(print_elements[:5]):
        onclick = elem.get('onclick', '')
        print(f"  Element {i+1} onclick: {onclick[:100]}...")
    
    # Also look for any href patterns
    rule_links = soup.find_all('a', href=re.compile(r'rule', re.IGNORECASE))
    print(f"  Found {len(rule_links)} links containing 'rule'")
    
    for i, link in enumerate(rule_links[:3]):
        href = link.get('href', '')
        text = link.get_text().strip()[:50]
        print(f"  Link {i+1}: {text} -> {href}")
    
    print()
    
    # 5. Look for the overall structure
    print("5. OVERALL STRUCTURE:")
    
    # Find main content area
    main_content = soup.find('div', {'id': re.compile(r'content|main', re.IGNORECASE)})
    if not main_content:
        main_content = soup.find('div', class_=re.compile(r'content|main', re.IGNORECASE))
    
    if main_content:
        print("  Found main content area")
        
        # Look for list structures
        lists = main_content.find_all(['ul', 'ol', 'table'])
        print(f"  Contains {len(lists)} list/table structures")
        
        for i, lst in enumerate(lists[:2]):
            items = lst.find_all(['li', 'tr'])
            if items:
                print(f"    List {i+1}: {len(items)} items")
                # Check first item for rule content
                first_item_text = items[0].get_text().strip()[:100]
                if 'rule' in first_item_text.lower():
                    print(f"      Sample: {first_item_text}...")
    
    print()
    
    # 6. Save sample HTML for detailed analysis
    print("6. SAVING SAMPLE HTML:")
    with open('D:\\work\\AI\\ita\\scripts\\experiments\\rules_page_sample.html', 'w', encoding='utf-8') as f:
        f.write(response.text[:50000])  # First 50k characters
    print("  Saved first 50k characters to rules_page_sample.html")

if __name__ == "__main__":
    explore_rules_page()