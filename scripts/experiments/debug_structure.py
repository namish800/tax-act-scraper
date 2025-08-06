"""
Debug script to examine the HTML structure around print buttons
"""

import requests
from bs4 import BeautifulSoup
import re

def debug_structure():
    url = "https://incometaxindia.gov.in/Pages/acts/income-tax-act.aspx"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    response = requests.get(url, headers=headers, timeout=30)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Find first print button
    print_button = soup.find('a', {'onclick': lambda x: x and 'PrintSection' in x})
    
    if print_button:
        print("=== FIRST PRINT BUTTON FOUND ===")
        print("Print button:", print_button)
        print()
        
        print("=== PARENT HIERARCHY ===")
        current = print_button
        level = 0
        
        while current and level < 5:
            print(f"Level {level}: {current.name}")
            if current.get('class'):
                print(f"  Classes: {current.get('class')}")
            
            # Look for dt-text-info-p in current element
            desc_elem = current.find('p', class_='dt-text-info-p')
            if desc_elem:
                print(f"  Found description: {desc_elem.get_text().strip()}")
            
            # Look for all p elements
            all_p = current.find_all('p', limit=5)
            if all_p:
                print(f"  P elements found: {len(all_p)}")
                for i, p in enumerate(all_p):
                    print(f"    P{i}: class='{p.get('class')}', text='{p.get_text().strip()[:50]}...'")
            
            current = current.parent
            level += 1
            print()

if __name__ == "__main__":
    debug_structure()