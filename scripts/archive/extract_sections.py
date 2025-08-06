"""
Script to crawl all section links from the Income‑tax Act, 1961 page on
incometaxindia.gov.in and save them to an Excel spreadsheet.  The page
lists every section of the Act with a small "open" icon in the upper
right corner of each section card.  Clicking this icon opens the
full text of that section in a new viewer.aspx page.  The script
automates clicking each open icon, capturing the resulting URL,
normalizing the section name (e.g., ``section_1``, ``section_80c``)
and writing the pairs to an Excel file.

Key features:

* Uses Selenium WebDriver in headless mode to navigate the site
  programmatically.
* Iterates through all pages of the Act (the site paginates the
  section cards—around 90+ pages).
* For each section card, extracts the visible heading, strips
  whitespace and punctuation to produce a normalized identifier
  prefixed with ``section_``.
* Clicks the "open" icon to launch the section text in a new tab,
  captures the resulting URL from the address bar, then closes the
  tab before continuing.
* Writes the collected data to ``income_tax_act_sections.xlsx`` with
  columns ``section_name`` and ``url``.

Dependencies::

    pip install selenium webdriver-manager pandas openpyxl

Note: This script should be run in an environment with internet
access.  It automates a real browser session, so execution may take
several minutes to cycle through all sections.
"""

import time
import json
import re
from typing import List, Dict

import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

try:
    from webdriver_manager.chrome import ChromeDriverManager  # type: ignore
    from selenium.webdriver.chrome.service import Service
    HAVE_WDM = True
except Exception:
    HAVE_WDM = False


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
    # Remove the word "Section" and dashes/colons.
    # Retain letters, numbers and dots (for sub‑sections like 80DD).  Use
    # regex to find the part after the word "Section".
    match = re.search(r"Section\s*[-:]*\s*(.+)", raw, re.IGNORECASE)
    identifier = match.group(1) if match else raw
    # Remove spaces and convert to lowercase.
    identifier = re.sub(r"\s+", "", identifier)
    return f"section_{identifier.lower()}"


def extract_sections(driver: webdriver.Chrome) -> List[Dict[str, str]]:
    """Scrape all section names and URLs from the Income‑tax Act page.

    Parameters
    ----------
    driver : webdriver.Chrome
        A Selenium WebDriver instance already navigated to the
        income‑tax act listing page.

    Returns
    -------
    List[Dict[str, str]]
        List of dictionaries with ``section_name`` and ``url`` keys.
    """
    wait = WebDriverWait(driver, 30)
    results: List[Dict[str, str]] = []

    print("Waiting for page to load...")
    time.sleep(5)  # Give page time to load
    
    print("Current URL:", driver.current_url)
    print("Page title:", driver.title)
    
    # Try to find pagination info with multiple selectors
    pagination_info = None
    try:
        pagination_info = wait.until(
            EC.presence_of_element_located((By.XPATH, "//div[contains(text(),'Page [')]"))
        )
    except:
        try:
            # Alternative selectors for pagination
            pagination_info = driver.find_element(By.CSS_SELECTOR, ".pagination-info")
        except:
            try:
                pagination_info = driver.find_element(By.XPATH, "//*[contains(text(),'of')]")
            except:
                print("Could not find pagination info, assuming single page")
                total_pages = 1
                pagination_info = None
    
    if pagination_info:
        text = pagination_info.text
        print("Pagination text:", text)
        # Extract number of pages.
        m = re.search(r"of\s*(\d+)", text)
        total_pages = int(m.group(1)) if m else 1
    else:
        total_pages = 1
    
    print(f"Total pages found: {total_pages}")

    for page_num in range(1, total_pages + 1):
        print(f"Processing page {page_num}...")
        
        # Try multiple selectors for cards
        cards = []
        try:
            wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div.card")))
            cards = driver.find_elements(By.CSS_SELECTOR, "div.card")
        except:
            # Try alternative selectors
            cards = driver.find_elements(By.CSS_SELECTOR, ".card")
            if not cards:
                cards = driver.find_elements(By.CSS_SELECTOR, "[class*='card']")
            if not cards:
                print("No cards found with standard selectors, searching for any div elements...")
                cards = driver.find_elements(By.TAG_NAME, "div")[:10]  # Limit to first 10 for testing
        
        print(f"Found {len(cards)} cards on page {page_num}")
        for card in cards:
            # Find the heading containing the section number.
            try:
                header = card.find_element(By.CSS_SELECTOR, "h4").text
            except Exception:
                continue
            normalized = normalize_section_name(header)
            # Locate the open icon (assume it is the last <a> within the card header icons).
            # Many of the icons have tooltips; we can pick by aria-label or by CSS class
            # containing 'fa-external' if FontAwesome is used.
            try:
                open_icon = card.find_element(By.CSS_SELECTOR, "div.card-header a:last-child")
            except Exception:
                # Fallback: attempt to match by title attribute containing "open".
                icons = card.find_elements(By.CSS_SELECTOR, "div.card-header a")
                open_icon = None
                for ic in icons:
                    title = ic.get_attribute("title") or ""
                    if "open" in title.lower():
                        open_icon = ic
                        break
                if open_icon is None:
                    continue

            # Open the section in a new tab using Ctrl + Click to avoid interfering with the main page.
            webdriver.ActionChains(driver).key_down(Keys.CONTROL).click(open_icon).key_up(Keys.CONTROL).perform()
            # Switch to the new tab (the last handle).
            driver.switch_to.window(driver.window_handles[-1])
            # Capture URL.  Wait until it navigates to a viewer page (begins with the base site)
            try:
                wait.until(lambda d: "viewer.aspx" in d.current_url)
            except Exception:
                pass
            url = driver.current_url
            results.append({"section_name": normalized, "url": url})
            # Close the new tab and return to the main listing tab.
            driver.close()
            driver.switch_to.window(driver.window_handles[0])

        # If not the last page, click the next page arrow.
        if page_num < total_pages:
            # Scroll to top to ensure the next button is visible.
            driver.execute_script("window.scrollTo(0, 0);")
            next_btn = wait.until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "button[aria-label='Next Page'], a[aria-label='Next']"))
            )
            next_btn.click()
            # Give time for the new page to load before continuing.
            time.sleep(1)

    return results


def main() -> None:
    url = "https://incometaxindia.gov.in/Pages/acts/income-tax-act.aspx"
    options = webdriver.ChromeOptions()
    # options.add_argument("--headless")  # Commented out to see browser
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    if HAVE_WDM:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
    else:
        driver = webdriver.Chrome(options=options)
    try:
        driver.get(url)
        data = extract_sections(driver)
    finally:
        driver.quit()

    # Save data to Excel.
    df = pd.DataFrame(data)
    df.to_excel("income_tax_act_sections.xlsx", index=False)
    print(f"Extracted {len(df)} sections and saved to income_tax_act_sections.xlsx")


if __name__ == "__main__":
    main()