"""
Script to explore the "Show Related Rules and Contents" functionality
on the Income Tax Act page to understand how to extract rules and forms data.
"""

import requests
from bs4 import BeautifulSoup
import re
import json

def explore_rules_and_forms():
    url = "https://incometaxindia.gov.in/Pages/acts/income-tax-act.aspx"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    response = requests.get(url, headers=headers, timeout=30)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    print("=== EXPLORING RELATED RULES AND FORMS ===\n")
    
    # Look for "Show Related Rules and Contents" links
    rules_links = soup.find_all('a', string=re.compile(r'Show Related Rules', re.IGNORECASE))
    print(f"Found {len(rules_links)} 'Show Related Rules' links")
    
    for i, link in enumerate(rules_links[:3]):  # Check first 3
        print(f"\nRules Link {i+1}:")
        print(f"  Text: {link.get_text().strip()}")
        print(f"  Href: {link.get('href', 'N/A')}")
        print(f"  Onclick: {link.get('onclick', 'N/A')}")
        
        # Look at parent structure
        parent_li = link.find_parent('li')
        if parent_li:
            print(f"  Parent LI classes: {parent_li.get('class', [])}")
            
            # Look for section info in the same parent
            section_p = parent_li.find('p', class_='dt-text-info-p')
            if section_p:
                print(f"  Related section: {section_p.get_text().strip()}")
    
    print("\n" + "="*50)
    
    # Look for any forms-related elements
    forms_elements = soup.find_all(text=re.compile(r'form|Form', re.IGNORECASE))
    print(f"Found {len(forms_elements)} elements mentioning 'form'")
    
    # Look for any onclick handlers that might show additional content
    onclick_elements = soup.find_all(attrs={'onclick': True})
    print(f"\nFound {len(onclick_elements)} elements with onclick handlers")
    
    # Look for specific patterns in onclick handlers
    show_content_handlers = [elem for elem in onclick_elements 
                           if elem.get('onclick') and 'show' in elem.get('onclick').lower()]
    
    print(f"Found {len(show_content_handlers)} elements with 'show' in onclick")
    
    for i, elem in enumerate(show_content_handlers[:5]):
        print(f"\nShow Handler {i+1}:")
        print(f"  Element: {elem.name}")
        print(f"  Text: {elem.get_text().strip()[:50]}...")
        print(f"  Onclick: {elem.get('onclick')}")
    
    # Look for any data attributes that might contain section IDs
    data_elements = soup.find_all(attrs=lambda x: x and any(k.startswith('data-') for k in x.keys()))
    print(f"\nFound {len(data_elements)} elements with data attributes")
    
    for i, elem in enumerate(data_elements[:3]):
        data_attrs = {k: v for k, v in elem.attrs.items() if k.startswith('data-')}
        if data_attrs:
            print(f"Data Element {i+1}: {elem.name}")
            for k, v in data_attrs.items():
                print(f"  {k}: {v}")

if __name__ == "__main__":
    explore_rules_and_forms()