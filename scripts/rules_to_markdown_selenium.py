"""
Selenium Rules → Markdown (Parallel)

Reads output/data/income_tax_rules.json, fetches each rule_url using Selenium
with retry/backoff to bypass 503s, converts to Markdown, and writes:
- output/data/income_tax_rules_with_content.json
- output/excel/income_tax_rules_with_content.xlsx
- output/markdown/rules/<normalized_rule_name>.md

CLI:
  python scripts/rules_to_markdown_selenium.py --test 10 --workers 4 --headless
"""

from __future__ import annotations

import argparse
import json
import random
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from threading import Lock, local
from typing import Any, Dict, Iterable, List, Optional, Tuple

import html2text
import pandas as pd
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

try:
    from webdriver_manager.chrome import ChromeDriverManager
    HAVE_WDM = True
except Exception:
    HAVE_WDM = False


DEFAULT_INPUT_JSON = Path("output/data/income_tax_rules.json")
OUT_JSON = Path("output/data/income_tax_rules_with_content.json")
OUT_EXCEL = Path("output/excel/income_tax_rules_with_content.xlsx")
OUT_MD_DIR = Path("output/markdown/rules")


def sanitize_filename(name: str) -> str:
    name = name.strip()
    name = re.sub(r"[\\/:*?\"<>|]", "_", name)
    # Replace hyphens/dashes with underscore as requested
    name = name.replace("-", "_").replace("–", "_").replace("—", "_")
    name = re.sub(r"\s+", "_", name)
    return name[:200]


def normalize_fallback(rule_name: str) -> str:
    ascii_name = rule_name.strip().encode("ascii", "ignore").decode("ascii")
    # Remove hyphens/dashes
    ascii_name = ascii_name.replace("-", " ").replace("–", " ").replace("—", " ")
    ascii_name = re.sub(r"\s+", " ", ascii_name)
    ascii_name = re.sub(r"^\s*-\s*", "", ascii_name)
    return ascii_name


def make_normalized_name(name: str) -> str:
    """Produce a lowercase, underscore-separated identifier without dashes.

    Collapses any sequence of non-alphanumeric characters to a single underscore
    and trims leading/trailing underscores. Ensures stable names like 'rule_1'.
    """
    if not name:
        return ""
    ascii_name = name.strip().encode("ascii", "ignore").decode("ascii")
    # Convert dashes to spaces first
    ascii_name = ascii_name.replace("-", " ").replace("–", " ").replace("—", " ")
    # Replace non-alphanumeric with underscore
    ascii_name = re.sub(r"[^A-Za-z0-9]+", "_", ascii_name)
    # Collapse multiple underscores and trim
    ascii_name = re.sub(r"_+", "_", ascii_name).strip("_")
    return ascii_name.lower()


def load_rules(input_json: Path) -> List[Dict[str, Any]]:
    if not input_json.exists():
        raise FileNotFoundError(f"Rules JSON not found: {input_json}")
    with input_json.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError("Expected a list of rule objects in the JSON file")
    return data


class SeleniumPool:
    """Thread-local Selenium driver pool with robust options."""

    def __init__(self, headless: bool, page_load_timeout: int = 60):
        self.local: local = local()
        self.headless = headless
        self.page_load_timeout = page_load_timeout

    def get_driver(self) -> webdriver.Chrome:
        if getattr(self.local, "driver", None) is None:
            self.local.driver = self._create_driver()
            self.local.wait = WebDriverWait(self.local.driver, 30)
        return self.local.driver

    def get_wait(self) -> WebDriverWait:
        self.get_driver()
        return self.local.wait  # type: ignore[attr-defined]

    def _create_driver(self) -> webdriver.Chrome:
        options = webdriver.ChromeOptions()
        if self.headless:
            options.add_argument("--headless=new")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"]) 
        options.add_experimental_option("useAutomationExtension", False)
        options.add_argument("--lang=en-US,en")
        options.add_argument("--disable-extensions")
        options.add_argument("--disable-logging")
        # Rotate user agents lightly
        user_agent = random.choice([
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
        ])
        options.add_argument(f"--user-agent={user_agent}")

        if HAVE_WDM:
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=options)
        else:
            driver = webdriver.Chrome(options=options)

        # Try to reduce detection
        try:
            driver.execute_script(
                "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
            )
        except Exception:
            pass

        driver.set_page_load_timeout(self.page_load_timeout)
        return driver

    def cleanup(self) -> None:
        driver = getattr(self.local, "driver", None)
        if driver is not None:
            try:
                driver.quit()
            except Exception:
                pass
            finally:
                self.local.driver = None


class RulesSeleniumMarkdownFetcher:
    def __init__(
        self,
        pool: SeleniumPool,
        max_retries: int = 4,
        base_delay: float = 6.0,
        selector_threshold: int = 300,
    ):
        self.pool = pool
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.selector_threshold = selector_threshold

        self.html_converter = html2text.HTML2Text()
        self.html_converter.ignore_links = False
        self.html_converter.ignore_images = True
        self.html_converter.ignore_emphasis = False
        self.html_converter.body_width = 0

        self.progress_lock = Lock()
        self.completed = 0

    def _backoff(self, attempt: int) -> None:
        delay = self.base_delay * (attempt + 1) + random.uniform(0, 1.5)
        time.sleep(delay)

    def _extract_content_node(self, soup: BeautifulSoup) -> BeautifulSoup:
        selectors = [
            'main', '[role="main"]', '.content', '#content', '.main-content',
            '.rule-content', '.rules-content', 'article', '.container', 'body'
        ]
        for sel in selectors:
            node = soup.select_one(sel)
            if node and len(node.get_text(strip=True)) >= self.selector_threshold:
                return node
        return soup.find('body') or soup

    def _clean_markdown(self, markdown: str) -> str:
        if not markdown:
            return ""
        markdown = re.sub(r"\n{3,}", "\n\n", markdown)
        markdown = re.sub(r"<!--.*?-->", "", markdown, flags=re.DOTALL)
        markdown = re.sub(r"\n\s*\|\s*\n", "\n", markdown)
        markdown = re.sub(r"\[\s*\]\(\s*\)", "", markdown)
        markdown = markdown.strip()
        return markdown

    def fetch_markdown(self, url: str) -> Tuple[bool, str, str, int]:
        last_error = ""
        for attempt in range(self.max_retries):
            try:
                driver = self.pool.get_driver()
                wait = self.pool.get_wait()
                driver.get(url)

                # Basic readiness
                wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
                time.sleep(2 + random.uniform(0, 1.0))

                page_title = driver.title or ""

                html = driver.page_source or ""
                if (
                    "503" in page_title
                    or "Service Unavailable" in page_title
                    or len(html) < 1000
                    or "Service Unavailable" in html
                ):
                    last_error = f"503 or short content (attempt {attempt+1})"
                    self._backoff(attempt)
                    # Light refresh on subsequent attempts
                    try:
                        driver.delete_all_cookies()
                    except Exception:
                        pass
                    continue

                soup = BeautifulSoup(html, "html.parser")
                for tag in soup(["script", "style", "nav", "header", "footer", "aside"]):
                    tag.decompose()
                node = self._extract_content_node(soup)
                raw_html = str(node)
                markdown = self.html_converter.handle(raw_html)
                markdown = self._clean_markdown(markdown)
                text_len = len(node.get_text(separator=" ", strip=True))
                return True, markdown, "", text_len

            except WebDriverException as e:
                last_error = f"WebDriver: {e.__class__.__name__}: {e}"
                self._backoff(attempt)
            except Exception as e:  # noqa: BLE001 - broad to ensure retries
                last_error = f"General: {e.__class__.__name__}: {e}"
                self._backoff(attempt)

        return False, "", last_error or "Unknown error", 0

    def process_one(self, rule: Dict[str, Any]) -> Dict[str, Any]:
        rule_name = rule.get("rule_name", "")
        rule_url = rule.get("rule_url", "")
        ok, md, err, n = self.fetch_markdown(rule_url)
        with self.progress_lock:
            self.completed += 1
            status = "OK" if ok else "FAIL"
            print(f"[{self.completed:4d}] {status}: {rule_name} ({n} chars)")
            if not ok and err:
                print(f"       Error: {err[:140]}")
        # Produce cleaned normalized name for outputs
        normalized_source = rule.get("normalized_rule_name") or normalize_fallback(rule.get("rule_name", ""))
        normalized_clean = make_normalized_name(normalized_source)
        return {
            "rule_name": rule.get("rule_name", ""),
            "normalized_rule_name": normalized_clean,
            "description": rule.get("description", ""),
            "rule_url": rule.get("rule_url", ""),
            "rule_id": rule.get("rule_id", ""),
            "page_number": rule.get("page_number", ""),
            "rule_content": md if ok else "",
            "content_success": ok,
            "content_error": "" if ok else err,
            "content_length": n,
        }


def save_outputs(results: List[Dict[str, Any]]) -> None:
    # JSON
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    with OUT_JSON.open("w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"JSON saved to: {OUT_JSON}")

    # Excel
    OUT_EXCEL.parent.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame(results)
    column_order = [
        "rule_name",
        "normalized_rule_name",
        "description",
        "rule_url",
        "rule_id",
        "page_number",
        "rule_content",
        "content_success",
        "content_error",
        "content_length",
    ]
    df = df[[c for c in column_order if c in df.columns]]
    df.to_excel(OUT_EXCEL, index=False, sheet_name="Rules")
    print(f"Excel saved to: {OUT_EXCEL}")

    # Markdown files
    OUT_MD_DIR.mkdir(parents=True, exist_ok=True)
    saved = 0
    for row in results:
        content = row.get("rule_content", "")
        if not content:
            continue
        normalized_raw = row.get("normalized_rule_name") or normalize_fallback(row.get("rule_name", ""))
        normalized = make_normalized_name(normalized_raw or "rule")
        filename = sanitize_filename(normalized) + ".md"
        (OUT_MD_DIR / filename).write_text(content, encoding="utf-8")
        saved += 1
    print(f"Markdown files saved to: {OUT_MD_DIR} ({saved} files)")


def run_parallel(rules: List[Dict[str, Any]], workers: int, headless: bool) -> List[Dict[str, Any]]:
    pool = SeleniumPool(headless=headless)
    fetcher = RulesSeleniumMarkdownFetcher(pool=pool)

    results: List[Dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = [executor.submit(fetcher.process_one, r) for r in rules]
        for fut in as_completed(futures):
            try:
                results.append(fut.result())
            except Exception as e:  # noqa: BLE001
                # Should not happen, but keep robust
                results.append({
                    "rule_content": "",
                    "content_success": False,
                    "content_error": f"Future error: {e}",
                })
    # Clean up one last time per thread
    pool.cleanup()
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch Income Tax Rules pages via Selenium and save Markdown/JSON/Excel")
    parser.add_argument("--input-json", type=str, default=str(DEFAULT_INPUT_JSON), help="Path to rules JSON")
    parser.add_argument("--test", type=int, default=None, help="Only process first N rules")
    parser.add_argument("--workers", type=int, default=4, help="Number of parallel workers")
    parser.add_argument("--headless", action="store_true", help="Run Chrome in headless mode")
    parser.add_argument("--batch-size", type=int, default=None, help="Process in batches of this size (sequential batches)")
    parser.add_argument("--batch-delay", type=float, default=8.0, help="Seconds to wait between batches")
    args = parser.parse_args()

    input_json = Path(args.input_json)
    # Avoid non-ASCII arrow to prevent UnicodeEncodeError on some consoles
    print("=== SELENIUM RULES -> MARKDOWN (PARALLEL) ===\n")
    print(f"Loading rules from: {input_json}")
    rules = load_rules(input_json)
    total = len(rules)
    if args.test is not None:
        rules = rules[: max(1, int(args.test))]
        print(f"Found {total} rules, TEST MODE on: taking first {len(rules)}\n")
    else:
        print(f"Found {total} rules\n")

    results: List[Dict[str, Any]] = []

    if args.batch_size and args.batch_size > 0 and args.batch_size < len(rules):
        total_batches = (len(rules) + args.batch_size - 1) // args.batch_size
        for b in range(total_batches):
            start = b * args.batch_size
            end = min(start + args.batch_size, len(rules))
            batch_rules = rules[start:end]
            print(f"\n--- Batch {b+1}/{total_batches}: rules [{start}:{end}) ---")
            batch_results = run_parallel(batch_rules, workers=max(1, args.workers), headless=args.headless)
            results.extend(batch_results)
            # Save incrementally after each batch
            save_outputs(results)
            if b < total_batches - 1 and args.batch_delay > 0:
                print(f"Waiting {args.batch_delay:.1f}s before next batch...")
                time.sleep(args.batch_delay)
    else:
        results = run_parallel(rules, workers=max(1, args.workers), headless=args.headless)
        save_outputs(results)
    print("\nCompleted!")


if __name__ == "__main__":
    main()


