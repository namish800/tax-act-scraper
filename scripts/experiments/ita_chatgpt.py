"""
This script uses Selenium WebDriver to automatically crawl the Income Tax
Department’s web site and extract the title and URL for each section of the
Income‑tax Act, 1961.  On the target page there are 94 pages containing
cards for each section.  Each card displays the section number and a short
description, along with a row of icons.  The rightmost icon opens the
full text of that section in a new tab.  By collecting the link behind
that icon, you obtain a stable URL for the section.

How it works
============

1.  The script launches a Chrome WebDriver and navigates to the list of
    sections: ``https://incometaxindia.gov.in/Pages/acts/income-tax-act.aspx``.
2.  A WebDriverWait is used to ensure the page is fully loaded before
    attempting to interact with it.
3.  On each page, the script locates all of the section cards using a
    CSS selector.  Within each card it extracts the title text and finds
    the anchor corresponding to the “open in new window” icon.  Many
    implementations use FontAwesome’s ``fa-arrow-up-right-from-square``
    class for this button – if the HTML changes you may need to adjust
    the selector.  The script attempts to read the link directly from
    the anchor’s ``href`` attribute; if this attribute is empty it
    programmatically opens the link in a new tab, grabs the URL from the
    address bar, then closes the tab.
4.  After processing all cards on the current page, the script clicks
    the “Next” button to advance.  When no further pages are available
    it breaks out of the loop.
5.  All collected records are written to a CSV file named
    ``income_tax_act_sections.csv`` in the current working directory.

Before running the script you need to install Selenium and have
chromedriver available in your ``PATH``.  On many systems the following
commands will prepare the environment::

    pip install selenium
    # download chromedriver from https://chromedriver.chromium.org/ and
    # ensure it matches your installed Chrome version
    # add it to your PATH or provide the executable_path to WebDriver

Usage
-----

Run the script with Python 3.  It will launch Chrome, extract all
sections and save them to ``income_tax_act_sections.csv``::

    python extract_income_tax_sections.py

Note: the website employs dynamic loading and may occasionally present
pop‑ups or banners.  If the script fails on a particular day, try
increasing the wait times or adjusting the CSS selectors.
"""

from __future__ import annotations

import csv
import time
from dataclasses import dataclass
from typing import List

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


@dataclass
class Section:
    """Simple data structure to hold a section's title and URL."""

    title: str
    url: str


class IncomeTaxActScraper:
    """Scrape section titles and URLs from the Income‑tax Act, 1961 listing."""

    def __init__(self, driver: webdriver.Chrome) -> None:
        self.driver = driver
        self.wait = WebDriverWait(driver, 20)
        self.sections: List[Section] = []

    def open_listing(self) -> None:
        """Navigate to the listing page."""
        self.driver.get(
            "https://incometaxindia.gov.in/Pages/acts/income-tax-act.aspx"
        )
        
        # Try multiple selectors to find the page content
        selectors_to_try = [
            "div[id^='section-']",  # Original selector
            ".section-card",         # Common class name
            ".card",                 # Generic card class
            "[data-section]",        # Data attribute
            ".act-section",          # Act-specific class
            "div.row div.col",       # Bootstrap-style layout
            "main",                  # Main content area
            "body"                   # Fallback to body
        ]
        
        element_found = False
        for selector in selectors_to_try:
            try:
                print(f"Trying selector: {selector}")
                self.wait.until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                )
                print(f"Found elements with selector: {selector}")
                element_found = True
                break
            except Exception as e:
                print(f"Selector {selector} failed: {str(e)}")
                continue
        
        if not element_found:
            print("No elements found with any selector. Page may have changed structure.")
            # Take a screenshot for debugging
            self.driver.save_screenshot("debug_screenshot.png")
            print("Screenshot saved as debug_screenshot.png")

    def extract_current_page(self) -> None:
        """Extract all sections on the current page."""
        # Try multiple selectors to find section cards
        card_selectors = [
            "div[id^='section-']",  # Original selector
            ".section-card",         # Common class name
            ".card",                 # Generic card class
            "[data-section]",        # Data attribute
            ".act-section",          # Act-specific class
            "div.row div.col",       # Bootstrap-style layout
        ]
        
        cards = []
        for selector in card_selectors:
            cards = self.driver.find_elements(By.CSS_SELECTOR, selector)
            if cards:
                print(f"Found {len(cards)} cards using selector: {selector}")
                break
        
        if not cards:
            print("No section cards found with any selector")
            return
            
        for card in cards:
            try:
                # The heading typically follows the format "Section - X" on its own line.
                heading_elem = card.find_element(By.CSS_SELECTOR, "h3")
                title = heading_elem.text.strip()
            except Exception:
                # Fallback: use the text of the card itself if h3 is missing.
                title = card.text.split("\n")[0].strip()

            # Find all links in the action bar of the card
            link_elems = card.find_elements(By.TAG_NAME, "a")
            section_url = ""
            for link in link_elems:
                href = link.get_attribute("href")
                # The section link typically points to viewer.aspx with cval parameter
                if href and "viewer.aspx" in href:
                    section_url = href
                    break
            # If we didn't find the URL in the href attribute, click the last link
            if not section_url and link_elems:
                # Click the last anchor which is usually the external link icon
                link_elems[-1].click()
                time.sleep(2)
                self.driver.switch_to.window(self.driver.window_handles[-1])
                section_url = self.driver.current_url
                self.driver.close()
                self.driver.switch_to.window(self.driver.window_handles[0])

            self.sections.append(Section(title=title, url=section_url))

    def go_to_next_page(self) -> bool:
        """Click the next page button.  Returns False if no next page is available."""
        try:
            # The navigation uses an anchor or button with aria-label="Next" or similar.
            next_btn = self.driver.find_element(By.CSS_SELECTOR, "button[aria-label='Next']")
        except Exception:
            # Some versions use an anchor with a specific class or id
            try:
                next_btn = self.driver.find_element(By.CSS_SELECTOR, "a[title='Next']")
            except Exception:
                # If no button is found, return False to stop looping
                return False

        # Scroll into view and click
        self.driver.execute_script("arguments[0].scrollIntoView(true);", next_btn)
        next_btn.click()
        # Wait for the page number to change by waiting for the first card to become stale
        time.sleep(1)
        return True

    def scrape(self) -> List[Section]:
        """Extract all sections across all pages."""
        self.open_listing()
        page_index = 1
        while True:
            print(f"Extracting page {page_index}...")
            self.extract_current_page()
            # Try moving to the next page
            if not self.go_to_next_page():
                break
            page_index += 1
        return self.sections


def main() -> None:
    # Set up Chrome options. Remove headless mode for debugging
    options = webdriver.ChromeOptions()
    # options.add_argument("--headless")  # Commented out for debugging
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    
    # Add user agent to avoid bot detection
    options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

    # Initialise the WebDriver.  If chromedriver is not in your PATH, provide
    # executable_path="/path/to/chromedriver".
    driver = webdriver.Chrome(options=options)
    try:
        scraper = IncomeTaxActScraper(driver)
        sections = scraper.scrape()
        print(f"Extracted {len(sections)} sections.")
        # Save results to a CSV file
        with open("income_tax_act_sections.csv", "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["Title", "URL"])
            for sec in sections:
                writer.writerow([sec.title, sec.url])
        print("Saved results to income_tax_act_sections.csv")
    finally:
        driver.quit()


if __name__ == "__main__":
    main()