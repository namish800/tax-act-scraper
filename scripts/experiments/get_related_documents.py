"""
Script to fetch related rules and forms for Income Tax Act sections
using the discovered web service endpoint.
"""

import requests
import json
from typing import Dict, List

def get_related_documents(section_id: str) -> Dict:
    """
    Fetch related documents (rules, forms, etc.) for a given section ID.
    
    Parameters:
    -----------
    section_id : str
        The section ID (e.g., '102120000000090711' for Section 2)
    
    Returns:
    --------
    Dict containing related documents data
    """
    
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
        
        # The response should be JSON
        data = response.json()
        return data
        
    except requests.RequestException as e:
        print(f"Error fetching related documents for section {section_id}: {e}")
        return {}
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON response for section {section_id}: {e}")
        print(f"Response content: {response.text[:200]}...")
        return {}

def test_related_documents():
    """Test the related documents functionality with known section IDs."""
    
    # Test with a few section IDs we know from the scraper
    test_sections = [
        ('102120000000090710', 'Section 1'),  # From the URL pattern we saw
        ('102120000000090711', 'Section 2'),  # This was in your example
        ('102120000000090712', 'Section 3'),
    ]
    
    print("=== TESTING RELATED DOCUMENTS API ===\n")
    
    for section_id, section_name in test_sections:
        print(f"Testing {section_name} (ID: {section_id})...")
        
        related_docs = get_related_documents(section_id)
        
        if related_docs:
            print(f"  Success! Got {len(str(related_docs))} characters of data")
            
            # Pretty print the structure to understand what we get
            print("  Data structure:")
            if isinstance(related_docs, dict):
                for key, value in related_docs.items():
                    if isinstance(value, list):
                        print(f"    {key}: [{len(value)} items]")
                    else:
                        print(f"    {key}: {type(value).__name__}")
            else:
                print(f"    Type: {type(related_docs)}")
            
            # Show first few characters of the response
            print(f"  Sample data: {str(related_docs)[:200]}...")
        else:
            print("  No data returned or error occurred")
        
        print()

def extract_section_id_from_url(section_url: str) -> str:
    """
    Extract the section ID from a section URL.
    
    Example:
    'https://incometaxindia.gov.in/acts/income-tax act, 1961/2025/102120000000090711.htm'
    -> '102120000000090711'
    """
    import re
    match = re.search(r'/(\d+)\.htm', section_url)
    if match:
        return match.group(1)
    return ""

if __name__ == "__main__":
    test_related_documents()
    
    # Also test the section ID extraction function
    print("\n=== TESTING SECTION ID EXTRACTION ===")
    test_url = "https://incometaxindia.gov.in/acts/income-tax act, 1961/2025/102120000000090711.htm"
    section_id = extract_section_id_from_url(test_url)
    print(f"URL: {test_url}")
    print(f"Extracted ID: {section_id}")