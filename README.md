# Income Tax Act Scraper

A comprehensive web scraper for extracting all sections of the Income Tax Act, 1961 from the official Income Tax India website, along with their related rules, forms, and FAQs.

## 📊 What This Scraper Does

- **Extracts 900+ sections** across 94 pages from [incometaxindia.gov.in](https://incometaxindia.gov.in/Pages/acts/income-tax-act.aspx)
- **Gets related documents** for each section:
  - Rules with direct URLs
  - Forms with download links  
  - FAQs with questions and answers
  - Notifications and circulars
- **Handles pagination** automatically using Selenium WebDriver
- **Outputs structured data** in Excel and JSON formats
- **Preserves relationships** between sections and rules/forms (duplicates are intentional)

## 🚀 Quick Start

### Prerequisites

```bash
pip install selenium webdriver-manager pandas openpyxl beautifulsoup4 requests
```

Or if using a virtual environment:
```bash
# Activate your virtual environment first, then:
python -m pip install -r requirements.txt
```

### Basic Usage

1. **Test Mode (3 pages)**:
   ```python
   python income_tax_scraper.py
   ```
   - Processes first 3 pages (~30 sections)
   - Takes ~5 minutes
   - Good for testing and validation

2. **Full Extraction (94 pages)**:
   - Open `income_tax_scraper.py`
   - Change `TEST_MODE = False`
   - Run the script
   - Takes 3-5 hours (~940 sections)

## 📁 Repository Structure

```
ita/
├── income_tax_scraper.py          # Main scraper (final version)
├── requirements.txt               # Dependencies
├── README.md                     # This file
├── output/
│   ├── excel/                   # Excel output files
│   └── data/                    # JSON data files
├── scripts/
│   ├── archive/                 # Older script versions
│   └── experiments/             # Development/debug scripts
└── docs/                        # Documentation
```

## 📋 Output Files

### Excel Output (`income_tax_complete.xlsx`)
- **Sections Summary**: All sections with metadata
- **Rules**: All related rules with URLs (includes duplicates to show which sections each rule applies to)
- **Forms**: All related forms with download links (includes duplicates to show relationships)
- **FAQs**: Frequently asked questions with answers

> **Note on Duplicates**: Rules and forms may appear multiple times because the same rule/form can apply to different sections. This preserves the important relationships between sections and their governing documents.

### JSON Output (`income_tax_complete.json`)
- Raw structured data
- Includes complete nested structure
- Useful for further processing

## 🎯 Sample Results

From our latest test (January 2025):
- **30 sections** (first 3 pages): **66 rule references**, **47 form references**, **23 FAQs**
- Example relationships preserved: "Rule 7" found in Section 2, "Rule 8" in multiple sections
- All pagination working correctly across pages 1-3
- ✅ **Test Status**: All functionality verified and working

## 🔧 Configuration Options

In `income_tax_scraper.py`:

```python
# Test mode (fast)
TEST_MODE = True
max_pages = 3

# Full extraction (slow but complete)
TEST_MODE = False  
max_pages = 94
```

## 🛠️ Technical Details

### How It Works

1. **Page Loading**: Uses Selenium to load the main Income Tax Act page
2. **Pagination**: Automatically clicks through all 94 pages
3. **Section Extraction**: Finds all sections and extracts:
   - Section name and title
   - Description
   - URL to full text
   - Internal section ID
4. **Related Documents**: For each section, calls the web service API:
   ```
   https://incometaxindia.gov.in/_vti_bin/taxmann.iti.webservices/DataWebService.svc/GetRelatedDocuments
   ```
5. **Data Processing**: Categorizes and structures all related documents
6. **Output Generation**: Creates Excel and JSON files with organized data

### Key Features

- **Robust Pagination**: Handles ASP.NET postback mechanism
- **Error Handling**: Continues processing if individual sections fail
- **Rate Limiting**: Includes delays to be respectful to the server
- **Unicode Handling**: Properly processes special characters
- **Structured Output**: Multiple Excel sheets for different data types
- **Relationship Preservation**: Keeps duplicates to show section-rule/form mappings

## 📈 Performance

- **Page 1**: ~10 sections, ~1 minute
- **Pages 1-3**: ~30 sections, ~5 minutes  
- **Pages 1-10**: ~100 sections, ~15 minutes
- **Full extraction**: ~940 sections, ~3-5 hours

## 🚨 Important Notes

1. **Server Respect**: The scraper includes delays between requests
2. **Headless Mode**: Runs Chrome in background by default
3. **Error Recovery**: Continues if individual pages fail
4. **Memory Usage**: Large datasets may require significant RAM
5. **Legal Use**: Only for legitimate research/reference purposes

## 🐛 Troubleshooting

### Common Issues

1. **Chrome Driver Issues**:
   ```bash
   pip install --upgrade webdriver-manager
   ```

2. **ModuleNotFoundError (pandas, etc.)**:
   ```bash
   # Make sure you're using the correct Python/virtual environment
   python -m pip install -r requirements.txt
   # Or run with specific Python path:
   /path/to/your/venv/Scripts/python.exe income_tax_scraper.py
   ```

2. **Memory Issues**: 
   - Process in smaller batches
   - Close other applications
   
3. **Network Timeouts**:
   - Check internet connection
   - Increase timeout values in script

4. **No Sections Found**:
   - Website structure may have changed
   - Check if site is accessible

## 📞 Support

If you encounter issues:
1. Check the `scripts/experiments/` folder for debug tools
2. Review the console output for specific error messages
3. Test with smaller page counts first
4. Ensure all dependencies are installed correctly

## ⚖️ Legal & Ethics

This scraper:
- ✅ Accesses publicly available information
- ✅ Includes respectful delays between requests
- ✅ Does not overwhelm the server
- ✅ Is for legitimate research/reference use

Please use responsibly and in accordance with the website's terms of service.

---

**Last Updated**: January 2025  
**Tested With**: Chrome WebDriver, Python 3.8+, Windows 10/11