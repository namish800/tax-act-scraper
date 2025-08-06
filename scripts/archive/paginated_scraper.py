"""
Comprehensive Income Tax Act scraper with pagination support.
Extracts all sections from all 90+ pages along with their related documents.
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
        print(f"Error fetching related documents for section {section_id}: {e}")
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
        
        if 'rule' in text_lower and href:  # Only rules with actual URLs
            result['rules'].append(document_info)
        elif 'form' in text_lower and href:
            result['forms'].append(document_info)
        elif 'notification' in text_lower and href:
            result['notifications'].append(document_info)
        elif 'circular' in text_lower and href:
            result['circulars'].append(document_info)
        elif not href or 'void(0)' in href:  # FAQs typically don't have real URLs
            result['faqs'].append(document_info)
        else:
            result['others'].append(document_info)
    
    return result

def get_total_pages(session: requests.Session, base_url: str) -> int:
    """Get the total number of pages from the pagination info."""
    try:
        response = session.get(base_url, timeout=30)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Look for pagination text like "931 Record(s) | Page [ 1 of 94]"
        pagination_text = soup.find(text=re.compile(r'of\s+\d+', re.IGNORECASE))
        if pagination_text:
            match = re.search(r'of\s+(\d+)', pagination_text, re.IGNORECASE)
            if match:
                return int(match.group(1))
        
        # Fallback: look for pagination elements
        pagination_links = soup.find_all('a', href=re.compile(r'page', re.IGNORECASE))
        if pagination_links:
            # Try to extract page numbers from links
            page_numbers = []
            for link in pagination_links:
                text = link.get_text().strip()
                if text.isdigit():
                    page_numbers.append(int(text))
            if page_numbers:
                return max(page_numbers)
        
        print("Could not determine total pages, defaulting to 1")
        return 1
        
    except Exception as e:
        print(f"Error getting total pages: {e}")
        return 1

def extract_sections_from_page(session: requests.Session, base_url: str, page_num: int) -> List[Dict[str, Any]]:
    """Extract sections from a specific page."""
    
    # For pages other than 1, we need to POST to get the specific page
    if page_num == 1:
        url = base_url
        response = session.get(url, timeout=30)
    else:
        # The website uses a POST mechanism for pagination
        # We need to simulate clicking the page number
        response = session.post(base_url, data={
            'ctl00$SPWebPartManager1$g_b48b8a2e_ffe5_43ff_ab75_55de58b3026a$ctl01$gvResults$ctl02$ctlPager$hdnPageNumber': str(page_num),
            '__EVENTTARGET': 'ctl00$SPWebPartManager1$g_b48b8a2e_ffe5_43ff_ab75_55de58b3026a$ctl01$gvResults$ctl02$ctlPager',
            '__EVENTARGUMENT': str(page_num)
        }, timeout=30)
    
    if response.status_code != 200:
        print(f"Error fetching page {page_num}: {response.status_code}")
        return []
    
    soup = BeautifulSoup(response.text, 'html.parser')
    page_results = []
    
    # Find all print buttons on this page
    print_buttons = soup.find_all('a', {'onclick': lambda x: x and 'PrintSection' in x})
    
    print(f"  Found {len(print_buttons)} sections on page {page_num}")
    
    for i, button in enumerate(print_buttons):
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
            
            print(f"    Processing {normalized_name}...")
            
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
            
            # Small delay between sections
            time.sleep(0.3)
    
    return page_results

def extract_all_sections_paginated(max_pages: int = None) -> List[Dict[str, Any]]:
    """Extract all sections from all pages with pagination support."""
    
    base_url = "https://incometaxindia.gov.in/Pages/acts/income-tax-act.aspx"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    # Create a session to maintain cookies and state
    session = requests.Session()
    session.headers.update(headers)
    
    print("Getting total number of pages...")
    total_pages = get_total_pages(session, base_url)
    print(f"Found {total_pages} total pages")
    
    if max_pages:
        total_pages = min(total_pages, max_pages)
        print(f"Limited to {total_pages} pages for testing")
    
    all_sections = []
    
    for page_num in range(1, total_pages + 1):
        print(f"\nProcessing page {page_num}/{total_pages}...")
        
        try:
            page_sections = extract_sections_from_page(session, base_url, page_num)
            all_sections.extend(page_sections)
            
            print(f"  Extracted {len(page_sections)} sections from page {page_num}")
            print(f"  Total sections so far: {len(all_sections)}")
            
            # Longer delay between pages to be respectful
            if page_num < total_pages:
                time.sleep(2)
                
        except Exception as e:
            print(f"  Error processing page {page_num}: {e}")
            continue
    
    return all_sections

def save_to_excel(sections_data: List[Dict[str, Any]], filename: str = "complete_income_tax_sections.xlsx"):
    """Save the comprehensive data to Excel with multiple sheets."""
    
    print(f"Saving data to {filename}...")
    
    # Create main sections sheet
    sections_df_data = []
    all_rules = []
    all_forms = []
    all_notifications = []
    all_circulars = []
    all_faqs = []
    all_others = []
    
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
            'notifications_count': section['notifications_count'],
            'circulars_count': section['circulars_count'],
            'faqs_count': section['faqs_count'],
            'others_count': section['others_count']
        })
        
        # Collect all related documents with section reference
        for rule in section['related_documents']['rules']:
            all_rules.append({
                'section_name': section['section_name'],
                'section_title': section['section_title'],
                'page_number': section['page_number'],
                'document_title': rule['title'],
                'document_url': rule['url'],
                'document_description': rule['description']
            })
        
        for form in section['related_documents']['forms']:
            all_forms.append({
                'section_name': section['section_name'],
                'section_title': section['section_title'],
                'page_number': section['page_number'],
                'document_title': form['title'],
                'document_url': form['url'],
                'document_description': form['description']
            })
        
        for notification in section['related_documents']['notifications']:
            all_notifications.append({
                'section_name': section['section_name'],
                'section_title': section['section_title'],
                'page_number': section['page_number'],
                'document_title': notification['title'],
                'document_url': notification['url'],
                'document_description': notification['description']
            })
        
        for circular in section['related_documents']['circulars']:
            all_circulars.append({
                'section_name': section['section_name'],
                'section_title': section['section_title'],
                'page_number': section['page_number'],
                'document_title': circular['title'],
                'document_url': circular['url'],
                'document_description': circular['description']
            })
        
        for faq in section['related_documents']['faqs']:
            all_faqs.append({
                'section_name': section['section_name'],
                'section_title': section['section_title'],
                'page_number': section['page_number'],
                'question': faq['title'],
                'description': faq['description']
            })
        
        for other in section['related_documents']['others']:
            all_others.append({
                'section_name': section['section_name'],
                'section_title': section['section_title'],
                'page_number': section['page_number'],
                'document_title': other['title'],
                'document_url': other['url'],
                'document_description': other['description']
            })
    
    # Create DataFrames
    sections_df = pd.DataFrame(sections_df_data)
    
    # Save to Excel with multiple sheets
    with pd.ExcelWriter(filename, engine='openpyxl') as writer:
        sections_df.to_excel(writer, sheet_name='Sections Summary', index=False)
        
        if all_rules:
            pd.DataFrame(all_rules).to_excel(writer, sheet_name='Rules', index=False)
        if all_forms:
            pd.DataFrame(all_forms).to_excel(writer, sheet_name='Forms', index=False)
        if all_notifications:
            pd.DataFrame(all_notifications).to_excel(writer, sheet_name='Notifications', index=False)
        if all_circulars:
            pd.DataFrame(all_circulars).to_excel(writer, sheet_name='Circulars', index=False)
        if all_faqs:
            pd.DataFrame(all_faqs).to_excel(writer, sheet_name='FAQs', index=False)
        if all_others:
            pd.DataFrame(all_others).to_excel(writer, sheet_name='Other Documents', index=False)
    
    print(f"Data saved to {filename}")
    print(f"Summary: {len(sections_data)} sections, {len(all_rules)} rules, {len(all_forms)} forms, {len(all_faqs)} FAQs")

def main():
    """Main function to run the paginated scraper."""
    print("Starting comprehensive Income Tax Act scraper with pagination...")
    print("This will extract ALL sections from ALL pages along with their related documents")
    print("WARNING: This may take a long time (potentially hours) and generate a large amount of data")
    print()
    
    # Start with 3 pages for testing
    max_pages = 3
    print("Testing with first 3 pages...")
    
    try:
        # Extract all sections with pagination
        sections_data = extract_all_sections_paginated(max_pages=max_pages)
        
        if sections_data:
            # Save to Excel
            filename = "test_income_tax_sections.xlsx" if max_pages else "complete_income_tax_sections.xlsx"
            save_to_excel(sections_data, filename)
            
            # Also save raw data as JSON
            json_filename = "test_income_tax_data.json" if max_pages else "complete_income_tax_data.json"
            with open(json_filename, 'w', encoding='utf-8') as f:
                json.dump(sections_data, f, indent=2, ensure_ascii=False)
            
            print(f"Successfully processed {len(sections_data)} sections")
            print(f"Data saved to {filename}")
            print(f"Raw data saved to {json_filename}")
        else:
            print("No sections were extracted")
            
    except Exception as e:
        print(f"Error during scraping: {e}")
        raise

if __name__ == "__main__":
    main()