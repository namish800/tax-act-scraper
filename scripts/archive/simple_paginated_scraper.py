"""
Simple paginated scraper that uses URL parameters to navigate pages.
Handles the ASP.NET postback pagination mechanism properly.
"""

import requests
from bs4 import BeautifulSoup
import pandas as pd
import json
import re
import time
from typing import List, Dict, Any

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
        print(f"      Error fetching related documents: {e}")
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
        
        # Handle JavaScript URLs - extract the actual URL from JavaScript function calls
        if href.startswith('javascript:'):
            js_url_match = re.search(r"'([^']+)'", href)
            if js_url_match:
                href = js_url_match.group(1)
            elif 'void(0)' in href:
                href = ''  # This is likely a FAQ or non-linked item
        
        # Get description from parent context
        parent = link.find_parent(['li', 'td', 'div'])
        description = ''
        if parent:
            parent_text = parent.get_text().strip()
            parent_text = parent_text.encode('ascii', 'ignore').decode('ascii')
            if len(parent_text) > len(text):
                description = parent_text.replace(text, '').strip()
                description = re.sub(r'\s+', ' ', description)  # Clean up whitespace
        
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

def extract_sections_from_page_simple(page_num: int) -> List[Dict[str, Any]]:
    """Extract sections using a simple approach - try direct page access."""
    
    # Try different URL patterns for pagination
    possible_urls = [
        f"https://incometaxindia.gov.in/Pages/acts/income-tax-act.aspx?page={page_num}",
        f"https://incometaxindia.gov.in/Pages/acts/income-tax-act.aspx?pagenum={page_num}",
        f"https://incometaxindia.gov.in/Pages/acts/income-tax-act.aspx?p={page_num}"
    ]
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    # If it's page 1, use the base URL
    if page_num == 1:
        url = "https://incometaxindia.gov.in/Pages/acts/income-tax-act.aspx"
    else:
        # For other pages, we'll need to simulate the postback
        # For now, let's just try the base URL and see if we can extract pagination links
        url = "https://incometaxindia.gov.in/Pages/acts/income-tax-act.aspx"
    
    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # If this is not page 1, we need a different approach
        if page_num > 1:
            print(f"    Note: Currently only processing page 1. Pagination requires session handling.")
            return []
        
        page_results = []
        
        # Find all print buttons on this page
        print_buttons = soup.find_all('a', {'onclick': lambda x: x and 'PrintSection' in x})
        
        print(f"    Found {len(print_buttons)} sections on page {page_num}")
        
        for i, button in enumerate(print_buttons, 1):
            onclick = button.get('onclick', '')
            
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
                button_li = button.find_parent('li', class_='ui-li')
                if button_li:
                    description_element = button_li.find('p', class_='dt-text-info-p')
                    if description_element:
                        section_description = description_element.get_text().strip()
                        section_description = section_description.encode('ascii', 'ignore').decode('ascii')
                
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
                time.sleep(0.5)
        
        return page_results
        
    except Exception as e:
        print(f"    Error processing page {page_num}: {e}")
        return []

def main():
    """Main function - for now just process page 1 as a test."""
    print("Simple Income Tax Act scraper - Processing page 1 only for now")
    print("This is a test to validate the data extraction works correctly")
    print()
    
    try:
        # Extract sections from page 1
        print("Processing page 1...")
        sections_data = extract_sections_from_page_simple(1)
        
        if sections_data:
            # Save to Excel
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
                    'total_related_documents': section['total_related_documents'],
                    'rules_count': section['rules_count'],
                    'forms_count': section['forms_count'],
                    'faqs_count': section['faqs_count']
                })
                
                # Collect rules and forms
                for rule in section['related_documents']['rules']:
                    all_rules.append({
                        'section_name': section['section_name'],
                        'section_title': section['section_title'],
                        'rule_title': rule['title'],
                        'rule_url': rule['url'],
                        'description': rule['description']
                    })
                
                for form in section['related_documents']['forms']:
                    all_forms.append({
                        'section_name': section['section_name'],
                        'section_title': section['section_title'],
                        'form_title': form['title'],
                        'form_url': form['url'],
                        'description': form['description']
                    })
                
                for faq in section['related_documents']['faqs']:
                    all_faqs.append({
                        'section_name': section['section_name'],
                        'section_title': section['section_title'],
                        'question': faq['title'],
                        'answer': faq['description']
                    })
            
            # Create DataFrames and save
            sections_df = pd.DataFrame(sections_df_data)
            
            filename = "page1_income_tax_sections.xlsx"
            with pd.ExcelWriter(filename, engine='openpyxl') as writer:
                sections_df.to_excel(writer, sheet_name='Sections', index=False)
                
                if all_rules:
                    pd.DataFrame(all_rules).to_excel(writer, sheet_name='Rules', index=False)
                if all_forms:
                    pd.DataFrame(all_forms).to_excel(writer, sheet_name='Forms', index=False)
                if all_faqs:
                    pd.DataFrame(all_faqs).to_excel(writer, sheet_name='FAQs', index=False)
            
            # Also save as JSON
            with open('page1_income_tax_data.json', 'w', encoding='utf-8') as f:
                json.dump(sections_data, f, indent=2, ensure_ascii=False)
            
            print(f"Successfully processed {len(sections_data)} sections from page 1")
            print(f"Found {len(all_rules)} rules, {len(all_forms)} forms, {len(all_faqs)} FAQs")
            print(f"Data saved to {filename}")
            print("Raw data saved to page1_income_tax_data.json")
            
        else:
            print("No sections were extracted")
            
    except Exception as e:
        print(f"Error during scraping: {e}")
        raise

if __name__ == "__main__":
    main()