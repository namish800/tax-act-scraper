"""
Script to extract Income Tax Act sections using Beautiful Soup.
Finds all sections and extracts URLs from the print button onclick attributes.
"""

import re
import requests
from bs4 import BeautifulSoup
import pandas as pd
from typing import List, Dict


def normalize_section_name(raw: str) -> str:
    """Normalize a section heading into a lowercase identifier.
    
    Examples
    --------
    >>> normalize_section_name('Section - 1')
    'section_1'
    >>> normalize_section_name('Section - 80C')
    'section_80c'
    """
    raw = raw.strip()
    # Remove the word "Section" and dashes/colons
    match = re.search(r"Section\s*[-:]*\s*(.+)", raw, re.IGNORECASE)
    identifier = match.group(1) if match else raw
    # Remove spaces and convert to lowercase
    identifier = re.sub(r"\s+", "", identifier)
    return f"section_{identifier.lower()}"


def extract_sections_from_html(html_content: str) -> List[Dict[str, str]]:
    """Extract section information from HTML content."""
    soup = BeautifulSoup(html_content, 'html.parser')
    results = []
    
    # Find all anchor tags with onclick containing PrintSection
    print_buttons = soup.find_all('a', {'onclick': lambda x: x and 'PrintSection' in x})
    
    for button in print_buttons:
        onclick = button.get('onclick', '')
        
        # Extract URL and section name from onclick attribute
        # Pattern: PrintSection('URL','en-US', 'Section Name')
        match = re.search(r"PrintSection\('([^']+)',\s*'[^']*',\s*'([^']+)'\)", onclick)
        
        if match:
            url = match.group(1)
            section_title = match.group(2)
            normalized_name = normalize_section_name(section_title)
            
            # Find the section description from the dt-text-info-p element
            section_description = ""
            
            # The description is in a sibling li element within the parent ul
            # Navigate up to find the li that contains this print button
            button_li = button.find_parent('li', class_='ui-li')
            if button_li:
                # Look for the p element with class dt-text-info-p in this li
                description_element = button_li.find('p', class_='dt-text-info-p')
                if description_element:
                    section_description = description_element.get_text().strip()
            
            results.append({
                'section_name': normalized_name,
                'section_title': section_title,
                'section_description': section_description,
                'url': url
            })
            print(f"Found: {normalized_name}")
            print(f"  Title: {section_title}")
            print(f"  Description: {section_description}")
            print(f"  URL: {url}")
            print()
    
    return results


def main():
    url = "https://incometaxindia.gov.in/Pages/acts/income-tax-act.aspx"
    
    print(f"Fetching content from: {url}")
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        print(f"Successfully fetched page (status: {response.status_code})")
        print(f"Content length: {len(response.text)} characters")
        
        sections = extract_sections_from_html(response.text)
        
        if sections:
            # Save to Excel
            df = pd.DataFrame(sections)
            df.to_excel("income_tax_act_sections_bs4.xlsx", index=False)
            print(f"Extracted {len(sections)} sections and saved to income_tax_act_sections_bs4.xlsx")
        else:
            print("No sections found. Let's examine the HTML structure...")
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Look for any onclick attributes
            all_onclick = soup.find_all(attrs={'onclick': True})
            print(f"Found {len(all_onclick)} elements with onclick attributes")
            
            # Look for print-related elements
            for element in all_onclick[:5]:  # Show first 5
                print(f"Element: {element.name}, onclick: {element.get('onclick')[:100]}...")
            
    except requests.RequestException as e:
        print(f"Error fetching the webpage: {e}")


if __name__ == "__main__":
    main()