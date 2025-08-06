"""
Script to explore the structure of the Income Tax Act page
"""

import requests
from bs4 import BeautifulSoup
import re

def explore_page():
    url = "https://incometaxindia.gov.in/Pages/acts/income-tax-act.aspx"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    response = requests.get(url, headers=headers, timeout=30)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    print("=== EXPLORING PAGE STRUCTURE ===\n")
    
    # Look for section cards/containers
    print("1. Looking for section containers...")
    cards = soup.find_all('div', class_=re.compile(r'card|section'))
    print(f"Found {len(cards)} potential section containers\n")
    
    # Look at first few cards to understand structure
    for i, card in enumerate(cards[:3]):
        print(f"Card {i+1}:")
        print(f"  Classes: {card.get('class', [])}")
        
        # Look for headings
        headings = card.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
        if headings:
            for h in headings:
                print(f"  Heading: {h.get_text().strip()}")
        
        # Look for print buttons
        print_btn = card.find('a', {'onclick': lambda x: x and 'PrintSection' in x})
        if print_btn:
            onclick = print_btn.get('onclick', '')
            match = re.search(r"PrintSection\('([^']+)',\s*'[^']*',\s*'([^']+)'\)", onclick)
            if match:
                print(f"  Print URL: {match.group(1)}")
                print(f"  Section Name: {match.group(2)}")
        print()
    
    # Look for pagination
    print("2. Looking for pagination...")
    pagination = soup.find_all(text=re.compile(r'page|Page|\d+\s*of\s*\d+', re.IGNORECASE))
    for p in pagination[:5]:
        print(f"  Pagination text: {p.strip()}")
    print()
    
    # Look for all onclick elements to understand the pattern better
    print("3. Analyzing all PrintSection onclick patterns...")
    onclick_elements = soup.find_all('a', {'onclick': lambda x: x and 'PrintSection' in x})
    
    for i, element in enumerate(onclick_elements[:10]):
        onclick = element.get('onclick', '')
        match = re.search(r"PrintSection\('([^']+)',\s*'[^']*',\s*'([^']+)'\)", onclick)
        if match:
            url = match.group(1)
            section_name = match.group(2)
            
            # Try to find the parent container and get more context
            parent_card = element.find_parent('div', class_=re.compile(r'card'))
            if parent_card:
                # Look for any text content that might be the full title
                text_content = parent_card.get_text(separator=' ').strip()
                lines = [line.strip() for line in text_content.split('\n') if line.strip()]
                
                print(f"Section {i+1}: {section_name}")
                print(f"  URL: {url}")
                print(f"  Card content: {lines[:3]}")  # First 3 lines
                print()

if __name__ == "__main__":
    explore_page()