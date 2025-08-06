"""
Analyze the rules page structure more deeply to understand the SetFormHierarchicalData pattern
"""

import requests
from bs4 import BeautifulSoup
import re

def analyze_rules_structure():
    url = "https://incometaxindia.gov.in/Pages/rules/income-tax-rules-1962.aspx"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    response = requests.get(url, headers=headers, timeout=30)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    print("=== DETAILED RULES STRUCTURE ANALYSIS ===\n")
    
    # 1. Look for SetFormHierarchicalData patterns
    print("1. SetFormHierarchicalData ANALYSIS:")
    page_source = response.text
    
    # Search for the function calls
    hierarchical_patterns = re.findall(r'SetFormHierarchicalData\([^)]+\)', page_source)
    print(f"  Found {len(hierarchical_patterns)} SetFormHierarchicalData calls")
    
    for i, pattern in enumerate(hierarchical_patterns[:5]):
        print(f"    {i+1}. {pattern}")
    
    print()
    
    # 2. Look for rule listings/tables
    print("2. RULE LISTINGS ANALYSIS:")
    
    # Look for table structures
    tables = soup.find_all('table')
    print(f"  Found {len(tables)} tables")
    
    for i, table in enumerate(tables):
        rows = table.find_all('tr')
        if rows:
            print(f"    Table {i+1}: {len(rows)} rows")
            
            # Check if this looks like a rules table
            for j, row in enumerate(rows[:3]):
                cells = row.find_all(['td', 'th'])
                if cells:
                    row_text = ' | '.join([cell.get_text().strip() for cell in cells])
                    row_text = row_text.encode('ascii', 'ignore').decode('ascii')
                    if 'rule' in row_text.lower() or j == 0:  # Header or contains rule
                        print(f"      Row {j+1}: {row_text[:100]}...")
    
    print()
    
    # 3. Look for dropdown/select elements with rules
    print("3. DROPDOWN/SELECT ANALYSIS:")
    
    selects = soup.find_all('select')
    print(f"  Found {len(selects)} select elements")
    
    for i, select in enumerate(selects):
        options = select.find_all('option')
        if options:
            print(f"    Select {i+1}: {len(options)} options")
            
            # Look for rule-related options
            rule_options = [opt for opt in options if 'rule' in opt.get_text().lower()]
            if rule_options:
                print(f"      {len(rule_options)} rule-related options")
                for j, opt in enumerate(rule_options[:5]):
                    text = opt.get_text().strip().encode('ascii', 'ignore').decode('ascii')
                    value = opt.get('value', '')
                    print(f"        {j+1}. {text} (value: {value})")
    
    print()
    
    # 4. Look for onclick handlers
    print("4. ONCLICK HANDLER ANALYSIS:")
    
    onclick_elements = soup.find_all(attrs={'onclick': True})
    print(f"  Found {len(onclick_elements)} elements with onclick")
    
    rule_onclick = [elem for elem in onclick_elements if 'rule' in elem.get('onclick', '').lower()]
    print(f"  Found {len(rule_onclick)} rule-related onclick handlers")
    
    for i, elem in enumerate(rule_onclick[:5]):
        onclick = elem.get('onclick', '')
        text = elem.get_text().strip().encode('ascii', 'ignore').decode('ascii')
        print(f"    {i+1}. Text: {text[:50]}...")
        print(f"       OnClick: {onclick}")
    
    print()
    
    # 5. Look for specific rule patterns in text
    print("5. RULE PATTERN ANALYSIS:")
    
    # Find all text containing rule numbers
    all_text = soup.get_text()
    rule_matches = re.findall(r'Rule\s*[-\s]*\d+[A-Z]*[^:\n]*:?[^\n]*', all_text, re.IGNORECASE)
    
    print(f"  Found {len(rule_matches)} potential rule entries")
    
    unique_rules = []
    for match in rule_matches:
        clean_match = match.strip().encode('ascii', 'ignore').decode('ascii')
        if clean_match and len(clean_match) > 10 and clean_match not in unique_rules:
            unique_rules.append(clean_match)
    
    for i, rule in enumerate(unique_rules[:10]):
        print(f"    {i+1}. {rule[:100]}...")
    
    print()
    
    # 6. Look for any URLs or links to individual rules
    print("6. RULE LINK ANALYSIS:")
    
    links = soup.find_all('a', href=True)
    rule_links = []
    
    for link in links:
        href = link.get('href', '')
        text = link.get_text().strip()
        
        if ('rule' in href.lower() or 'rule' in text.lower()) and len(text) > 5:
            rule_links.append({
                'text': text.encode('ascii', 'ignore').decode('ascii')[:50],
                'href': href
            })
    
    print(f"  Found {len(rule_links)} potential rule links")
    
    for i, link in enumerate(rule_links[:5]):
        print(f"    {i+1}. {link['text']} -> {link['href']}")

if __name__ == "__main__":
    analyze_rules_structure()