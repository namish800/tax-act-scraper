"""
Script to parse the HTML response from the related documents API
and extract structured information about rules, forms, and other related content.
"""

import requests
import json
from bs4 import BeautifulSoup
from typing import Dict, List
import re

def get_related_documents_html(section_id: str) -> str:
    """Fetch related documents HTML for a given section ID."""
    
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
        
        # The response is JSON containing HTML as a string
        data = response.json()
        return data if isinstance(data, str) else str(data)
        
    except Exception as e:
        print(f"Error fetching related documents for section {section_id}: {e}")
        return ""

def parse_related_documents(html_content: str) -> Dict[str, List[Dict]]:
    """
    Parse the HTML content and extract structured information about related documents.
    
    Returns:
    --------
    Dict with categories like 'rules', 'forms', 'notifications', etc.
    Each category contains a list of documents with title, description, and link.
    """
    
    if not html_content:
        return {}
    
    soup = BeautifulSoup(html_content, 'html.parser')
    result = {
        'rules': [],
        'forms': [],
        'notifications': [],
        'circulars': [],
        'others': []
    }
    
    # Look for different sections in the HTML
    # The structure might have ul/li elements or table elements containing the related documents
    
    # Find all links (a tags) in the content
    links = soup.find_all('a', href=True)
    
    for link in links:
        href = link.get('href', '')
        text = link.get_text().strip()
        
        if not text or len(text) < 5:  # Skip very short or empty links
            continue
        
        # Clean up text to handle Unicode issues
        text = text.encode('ascii', 'ignore').decode('ascii')
        
        # Handle JavaScript URLs - extract the actual URL from JavaScript function calls
        if href.startswith('javascript:'):
            import re
            js_url_match = re.search(r"'([^']+)'", href)
            if js_url_match:
                href = js_url_match.group(1)
        
        # Try to get additional context from parent elements
        parent = link.find_parent(['li', 'td', 'div'])
        description = ''
        if parent:
            parent_text = parent.get_text().strip()
            parent_text = parent_text.encode('ascii', 'ignore').decode('ascii')
            if len(parent_text) > len(text):
                # Extract description by removing the link text
                description = parent_text.replace(text, '').strip()
        
        # Categorize based on text content or URL patterns
        document_info = {
            'title': text,
            'url': href,
            'description': description
        }
        
        # Categorize the document
        text_lower = text.lower()
        href_lower = href.lower()
        
        if any(keyword in text_lower for keyword in ['rule', 'rules']):
            result['rules'].append(document_info)
        elif any(keyword in text_lower for keyword in ['form', 'forms']):
            result['forms'].append(document_info)
        elif any(keyword in text_lower for keyword in ['notification', 'notify']):
            result['notifications'].append(document_info)
        elif any(keyword in text_lower for keyword in ['circular']):
            result['circulars'].append(document_info)
        else:
            result['others'].append(document_info)
    
    # Also look for structured lists or tables
    lists = soup.find_all(['ul', 'ol'])
    for ul in lists:
        items = ul.find_all('li')
        for li in items:
            text = li.get_text().strip()
            if text and len(text) > 10:  # Only meaningful content
                
                # Look for links within this list item
                li_links = li.find_all('a', href=True)
                if li_links:
                    for li_link in li_links:
                        link_text = li_link.get_text().strip()
                        if link_text and link_text not in [doc['title'] for docs in result.values() for doc in docs]:
                            document_info = {
                                'title': link_text,
                                'url': li_link.get('href', ''),
                                'description': text.replace(link_text, '').strip()
                            }
                            
                            # Categorize
                            text_lower = text.lower()
                            if 'rule' in text_lower:
                                result['rules'].append(document_info)
                            elif 'form' in text_lower:
                                result['forms'].append(document_info)
                            elif 'notification' in text_lower:
                                result['notifications'].append(document_info)
                            elif 'circular' in text_lower:
                                result['circulars'].append(document_info)
                            else:
                                result['others'].append(document_info)
    
    return result

def test_parsing():
    """Test the parsing functionality with known section IDs."""
    
    test_sections = [
        ('102120000000090711', 'Section 2'),  # This one had a lot of data
        ('102120000000090712', 'Section 3'),
    ]
    
    print("=== TESTING RELATED DOCUMENTS PARSING ===\n")
    
    for section_id, section_name in test_sections:
        print(f"Parsing {section_name} (ID: {section_id})...")
        
        html_content = get_related_documents_html(section_id)
        
        if html_content:
            # Show raw HTML structure first
            soup = BeautifulSoup(html_content, 'html.parser')
            print(f"  Raw HTML length: {len(html_content)} characters")
            
            # Show the structure
            all_links = soup.find_all('a', href=True)
            print(f"  Found {len(all_links)} links in HTML")
            
            # Parse the documents
            parsed_docs = parse_related_documents(html_content)
            
            print("  Parsed results:")
            for category, docs in parsed_docs.items():
                if docs:
                    print(f"    {category}: {len(docs)} items")
                    for i, doc in enumerate(docs[:2]):  # Show first 2 items
                        print(f"      {i+1}. {doc['title'][:60]}...")
                        if doc['url']:
                            print(f"         URL: {doc['url']}")
            
            # Also show some raw content to understand the structure better
            print(f"  Raw content sample:")
            print(f"    {html_content[:300]}...")
            
        print("\n" + "="*50 + "\n")

if __name__ == "__main__":
    test_parsing()