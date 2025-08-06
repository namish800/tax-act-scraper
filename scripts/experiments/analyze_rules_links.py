"""
Script to analyze the "Show Related Rules and Contents" links 
and understand what data might be loaded dynamically.
"""

import requests
from bs4 import BeautifulSoup
import re
import json

def analyze_rules_functionality():
    url = "https://incometaxindia.gov.in/Pages/acts/income-tax-act.aspx"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    response = requests.get(url, headers=headers, timeout=30)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    print("=== ANALYZING RULES LINKS FUNCTIONALITY ===\n")
    
    # Look for JavaScript that might handle the "Show Related Rules" functionality
    scripts = soup.find_all('script')
    print(f"Found {len(scripts)} script tags")
    
    # Look for functions that might handle showing related content
    for i, script in enumerate(scripts):
        if script.string:
            script_content = script.string
            if any(keyword in script_content.lower() for keyword in ['show', 'rule', 'content', 'ajax', 'load']):
                print(f"\nScript {i+1} (relevant content):")
                print(f"Length: {len(script_content)} characters")
                # Show first few lines to understand the pattern
                lines = script_content.split('\n')[:10]
                for line in lines:
                    if line.strip():
                        print(f"  {line.strip()[:100]}...")
                        if len([l for l in lines if l.strip()]) > 5:
                            break
    
    print("\n" + "="*50)
    
    # Look for hidden divs or containers that might hold related content
    hidden_elements = soup.find_all(['div', 'section'], style=re.compile(r'display:\s*none', re.IGNORECASE))
    print(f"Found {len(hidden_elements)} hidden elements")
    
    for i, elem in enumerate(hidden_elements[:3]):
        print(f"\nHidden Element {i+1}:")
        print(f"  Tag: {elem.name}")
        print(f"  Classes: {elem.get('class', [])}")
        print(f"  ID: {elem.get('id', 'N/A')}")
        if elem.get_text().strip():
            print(f"  Content preview: {elem.get_text().strip()[:100]}...")
    
    print("\n" + "="*50)
    
    # Look for any elements with IDs that might be related to rules/forms
    elements_with_ids = soup.find_all(attrs={'id': True})
    relevant_ids = [elem for elem in elements_with_ids 
                   if any(keyword in elem.get('id', '').lower() 
                         for keyword in ['rule', 'form', 'content', 'related', 'show'])]
    
    print(f"Found {len(relevant_ids)} elements with relevant IDs")
    for elem in relevant_ids[:5]:
        print(f"  ID: {elem.get('id')}, Tag: {elem.name}")
    
    # Look at the structure around each "Show Related Rules" link more carefully
    print("\n" + "="*50)
    print("DETAILED ANALYSIS OF RULES LINKS:")
    
    rules_links = soup.find_all('a', string=re.compile(r'Show Related Rules', re.IGNORECASE))
    
    for i, link in enumerate(rules_links[:2]):  # Analyze first 2 in detail
        print(f"\n--- Rules Link {i+1} Analysis ---")
        
        # Get the full parent structure
        parent_ul = link.find_parent('ul', class_='dt-ui-info')
        if parent_ul:
            print(f"Parent UL found with classes: {parent_ul.get('class')}")
            
            # Look for any data attributes or IDs in the parent structure
            if parent_ul.get('id'):
                print(f"Parent UL ID: {parent_ul.get('id')}")
            
            # Look for any div elements that might contain the rules content
            sibling_divs = parent_ul.find_next_siblings('div')
            print(f"Found {len(sibling_divs)} sibling div elements")
            
            for j, div in enumerate(sibling_divs[:2]):
                print(f"  Sibling div {j+1}: classes={div.get('class', [])}, id={div.get('id', 'N/A')}")
                if div.get_text().strip():
                    print(f"    Content: {div.get_text().strip()[:100]}...")

if __name__ == "__main__":
    analyze_rules_functionality()