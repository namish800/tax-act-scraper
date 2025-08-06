"""
Income Tax Act Content Fetcher
Fetches HTML content from section URLs and converts to markdown format
"""

import pandas as pd
import requests
from bs4 import BeautifulSoup
import html2text
import re
import time
import json
from pathlib import Path
from typing import Dict, List, Optional

# Configuration
INPUT_EXCEL = "output/excel/selenium_income_tax_sections.xlsx"
TEST_MODE = False  # Set to False to process all sections
MAX_TEST_SECTIONS = 5  # Only used when TEST_MODE is True

class ContentFetcher:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
        
        # HTML to markdown converter
        self.html_converter = html2text.HTML2Text()
        self.html_converter.ignore_links = False
        self.html_converter.ignore_images = True
        self.html_converter.ignore_emphasis = False
        self.html_converter.body_width = 0  # No line wrapping
        
    def fetch_section_content(self, section_url: str, section_name: str, max_retries: int = 3) -> Dict[str, str]:
        """Fetch and parse content from a section URL with retry logic"""
        
        if not section_url or pd.isna(section_url):
            return {
                'success': False,
                'error': 'No URL provided',
                'html_content': '',
                'markdown_content': '',
                'cleaned_text': '',
                'content_length': 0,
                'attempts': 0
            }
        
        last_error = None
        
        for attempt in range(max_retries):
            try:
                if attempt > 0:
                    delay = 2 ** attempt  # Exponential backoff: 2s, 4s, 8s
                    print(f"    Retry {attempt + 1}/{max_retries} after {delay}s delay...")
                    time.sleep(delay)
                else:
                    print(f"    Fetching: {section_url}")
                
                # Fetch the page
                response = self.session.get(section_url, timeout=30)
                response.raise_for_status()
                
                # Parse HTML
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Remove unnecessary elements
                for element in soup(['script', 'style', 'nav', 'header', 'footer', 'aside']):
                    element.decompose()
                
                # Find main content area
                main_content = self._extract_main_content(soup)
                
                # Get raw HTML
                html_content = str(main_content)
                
                # Convert to markdown
                markdown_content = self.html_converter.handle(html_content)
                
                # Clean up markdown
                cleaned_markdown = self._clean_markdown(markdown_content)
                
                # Extract clean text
                cleaned_text = main_content.get_text(separator=' ', strip=True)
                cleaned_text = re.sub(r'\s+', ' ', cleaned_text)
                
                return {
                    'success': True,
                    'error': '',
                    'html_content': html_content[:5000],  # Limit size
                    'markdown_content': cleaned_markdown,
                    'cleaned_text': cleaned_text[:2000],  # Limit size
                    'content_length': len(cleaned_text),
                    'fetched_at': pd.Timestamp.now().isoformat(),
                    'attempts': attempt + 1
                }
                
            except requests.exceptions.Timeout as e:
                last_error = f'Timeout error: {str(e)}'
                print(f"    Timeout on attempt {attempt + 1}")
                
            except requests.exceptions.ConnectionError as e:
                last_error = f'Connection error: {str(e)}'
                print(f"    Connection error on attempt {attempt + 1}")
                
            except requests.exceptions.HTTPError as e:
                if e.response.status_code in [429, 503, 504]:  # Rate limiting or server errors
                    last_error = f'Server error {e.response.status_code}: {str(e)}'
                    print(f"    Server error {e.response.status_code} on attempt {attempt + 1}")
                else:
                    # Don't retry for client errors like 404
                    return {
                        'success': False,
                        'error': f'HTTP {e.response.status_code}: {str(e)}',
                        'html_content': '',
                        'markdown_content': '',
                        'cleaned_text': '',
                        'content_length': 0,
                        'attempts': attempt + 1
                    }
                    
            except requests.RequestException as e:
                last_error = f'Request error: {str(e)}'
                print(f"    Request error on attempt {attempt + 1}")
                
            except Exception as e:
                last_error = f'Parse error: {str(e)}'
                print(f"    Parse error on attempt {attempt + 1}")
        
        # All attempts failed
        return {
            'success': False,
            'error': f'Failed after {max_retries} attempts. Last error: {last_error}',
            'html_content': '',
            'markdown_content': '',
            'cleaned_text': '',
            'content_length': 0,
            'attempts': max_retries
        }
    
    def _extract_main_content(self, soup: BeautifulSoup) -> BeautifulSoup:
        """Extract main content from parsed HTML"""
        
        # Try to find main content area using common selectors
        content_selectors = [
            'main',
            '[role="main"]',
            '.content',
            '#content',
            '.main-content',
            '.section-content',
            '.act-content',
            'article',
            '.container .row',
            'body'  # Fallback
        ]
        
        for selector in content_selectors:
            content = soup.select_one(selector)
            if content:
                return content
        
        # If no specific content area found, return body
        return soup.find('body') or soup
    
    def _clean_markdown(self, markdown: str) -> str:
        """Clean up markdown content"""
        if not markdown:
            return ""
        
        # Remove excessive newlines
        markdown = re.sub(r'\n{3,}', '\n\n', markdown)
        
        # Remove HTML comments
        markdown = re.sub(r'<!--.*?-->', '', markdown, flags=re.DOTALL)
        
        # Clean up table formatting
        markdown = re.sub(r'\n\s*\|\s*\n', '\n', markdown)
        
        # Remove empty links
        markdown = re.sub(r'\[\s*\]\(\s*\)', '', markdown)
        
        # Strip whitespace
        markdown = markdown.strip()
        
        return markdown
    
    def process_sections(self, input_file: str) -> pd.DataFrame:
        """Process all sections from Excel file"""
        
        print("=== INCOME TAX ACT CONTENT FETCHER ===\n")
        
        # Load sections data
        print(f"Loading sections from: {input_file}")
        df = pd.read_excel(input_file)
        
        print(f"Found {len(df)} sections to process")
        
        if TEST_MODE:
            df = df.head(MAX_TEST_SECTIONS)
            print(f"TEST MODE: Processing first {len(df)} sections")
        
        print()
        
        # Add new columns for content
        df['content_success'] = False
        df['content_error'] = ''
        df['html_content'] = ''
        df['markdown_content'] = ''
        df['cleaned_text'] = ''
        df['content_length'] = 0
        df['fetched_at'] = ''
        df['attempts'] = 0
        
        # Process each section
        for idx, row in df.iterrows():
            section_name = row['section_name']
            section_url = row['section_url']
            
            print(f"Processing {idx+1}/{len(df)}: {section_name}")
            
            # Fetch content
            result = self.fetch_section_content(section_url, section_name)
            
            # Update dataframe
            df.at[idx, 'content_success'] = result['success']
            df.at[idx, 'content_error'] = result['error']
            df.at[idx, 'html_content'] = result['html_content']
            df.at[idx, 'markdown_content'] = result['markdown_content']
            df.at[idx, 'cleaned_text'] = result['cleaned_text']
            df.at[idx, 'content_length'] = result.get('content_length', 0)
            df.at[idx, 'fetched_at'] = result.get('fetched_at', '')
            df.at[idx, 'attempts'] = result.get('attempts', 0)
            
            if result['success']:
                print(f"    Success: {result.get('content_length', 0)} characters ({result.get('attempts', 1)} attempts)")
            else:
                print(f"    Failed: {result['error']}")
            
            # Be respectful to server - longer delay between requests
            time.sleep(2)
        
        return df
    
    def save_results(self, df: pd.DataFrame):
        """Save results to multiple formats"""
        
        print(f"\nSaving results...")
        
        # Save to Excel with content
        excel_file = "output/excel/income_tax_sections_with_content.xlsx"
        df.to_excel(excel_file, index=False)
        print(f"Excel saved to: {excel_file}")
        
        # Save to JSON
        json_file = "output/data/income_tax_sections_with_content.json"
        df.to_json(json_file, orient='records', indent=2)
        print(f"JSON saved to: {json_file}")
        
        # Save individual markdown files for successful sections
        markdown_dir = Path("output/markdown")
        markdown_dir.mkdir(exist_ok=True)
        
        successful_sections = df[df['content_success'] == True]
        
        for _, row in successful_sections.iterrows():
            section_name = row['section_name']
            markdown_content = row['markdown_content']
            
            if markdown_content:
                filename = f"{section_name}.md"
                filepath = markdown_dir / filename
                
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(f"# {row['section_title']}\n\n")
                    f.write(f"**URL:** {row['section_url']}\n\n")
                    f.write(f"**Description:** {row['section_description']}\n\n")
                    f.write("---\n\n")
                    f.write(markdown_content)
        
        print(f"Markdown files saved to: {markdown_dir}")
        
        # Print summary
        successful_count = len(successful_sections)
        failed_count = len(df) - successful_count
        
        print(f"\n=== SUMMARY ===")
        print(f"Total sections: {len(df)}")
        print(f"Successfully fetched: {successful_count}")
        print(f"Failed: {failed_count}")
        
        if failed_count > 0:
            print(f"\nFailed sections:")
            failed_sections = df[df['content_success'] == False]
            for _, row in failed_sections.iterrows():
                print(f"  - {row['section_name']}: {row['content_error']}")

def main():
    fetcher = ContentFetcher()
    
    # Process sections
    df = fetcher.process_sections(INPUT_EXCEL)
    
    # Save results
    fetcher.save_results(df)
    
    print(f"\nCompleted!")

if __name__ == "__main__":
    main()