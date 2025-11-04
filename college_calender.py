#!/usr/bin/env python3
"""
College Calendar Scraper for ASP.NET WebForms
Handles ViewState and pagination to fetch all class schedules
"""

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from bs4 import BeautifulSoup
import json
import time
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import unquote

# Configuration constants
ACADEMIC_YEAR_START_MONTH = 10  # October - when new academic year begins
SCRAPE_LOOKBACK_DAYS = 7  # How many days back to fetch classes

class CollegeCalendarScraper:
    def __init__(self, url, cookies):
        """
        Initialize the scraper

        Args:
            url: The URL of the calendar page
            cookies: Dictionary of cookies (BCI_OL_KEY, OrbitLivePresentationTypeByCookie, etc.)
        """
        self.url = url
        self.session = requests.Session()

        # Configure retry strategy
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "POST"]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

        # Set timeout for all requests (connect timeout, read timeout)
        self.timeout = (10, 30)

        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:144.0) Gecko/20100101 Firefox/144.0',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br, zstd',
            'Content-Type': 'application/x-www-form-urlencoded',
            'Origin': 'https://live.or-bit.net',
            'Referer': url,
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'same-origin',
            'Sec-Fetch-User': '?1',
        })

        # Set cookies
        for key, value in cookies.items():
            self.session.cookies.set(key, value)

        self.viewstate_data = {}

    def validate_session(self):
        """
        Validate that session cookies are working

        Returns:
            True if session is valid

        Raises:
            ValueError if session is invalid or cookies expired
        """
        try:
            print("Validating session cookies...")
            response = self.session.get(self.url, timeout=self.timeout)
            response.raise_for_status()

            # Check if we got redirected to login page
            if 'login' in response.url.lower():
                raise ValueError("Session cookies have expired - redirected to login page")

            # Check for typical login indicators in the HTML
            if 'כניסה למערכת' in response.text or 'התחברות' in response.text:
                raise ValueError("Session cookies are invalid - login page detected")

            print("Session validation successful")
            return True

        except requests.exceptions.RequestException as e:
            raise ValueError(f"Session validation failed: {e}")

    def extract_form_fields(self, html):
        """
        Extract ASP.NET form fields from HTML response

        Returns:
            Dictionary containing __VIEWSTATE, __EVENTVALIDATION, etc.
        """
        soup = BeautifulSoup(html, 'html.parser')

        fields = {}

        # Extract hidden form fields
        for field in ['__VIEWSTATE', '__EVENTVALIDATION', '__PageDataKey',
                     'tvMain_ExpandState', 'tvMain_SelectedNode']:
            element = soup.find('input', {'name': field})
            if element:
                fields[field] = element.get('value', '')

        # Extract other form fields that might be needed
        for select in soup.find_all('select'):
            name = select.get('name')
            if name:
                selected = select.find('option', selected=True)
                if selected:
                    fields[name] = selected.get('value', '')

        return fields

    def get_data_rows(self, html):
        """
        Extract the actual data rows from a page (excluding ViewState and metadata)

        Args:
            html: HTML content

        Returns:
            List of tuples containing the data rows
        """
        soup = BeautifulSoup(html, 'html.parser')

        # Find the data grid/table
        grid = soup.find('table', {'class': lambda x: x and 'GridView' in x}) or \
               soup.find('div', {'id': lambda x: x and 'gvData' in x}) or \
               soup.find('table')

        if not grid:
            return []

        # Get all data rows (skip header and pagination row)
        rows = []
        for row in grid.find_all('tr')[1:]:  # Skip header row
            # Check if this row is in a pagination table (tr/td with class="GridPager")
            if row.find_parent('tr', class_=lambda x: x and 'Pager' in x):
                continue

            cells = [cell.get_text(strip=True) for cell in row.find_all(['td', 'th'])]

            # Skip pagination row - check if row contains mostly numbers/pagination symbols
            # Count how many cells are pagination-related
            pagination_count = sum(
                1 for cell in cells
                if cell and (cell.isdigit() or cell in ['...', '›', '»', '‹', '«', '<', '>', '|'] or
                            all(c.isdigit() or c in '...' for c in cell))
            )

            # If more than half the non-empty cells are pagination-related, skip this row
            non_empty_cells = [c for c in cells if c]
            is_pagination = non_empty_cells and pagination_count > len(non_empty_cells) / 2

            if not is_pagination and cells:  # Skip empty rows too
                rows.append(tuple(cells))

        return rows

    def has_next_page(self, html, current_page):
        """
        Check if there's a next page available

        Args:
            html: Current page HTML
            current_page: Current page number

        Returns:
            True if there's a next page, False otherwise
        """
        soup = BeautifulSoup(html, 'html.parser')

        # Look for pagination links
        page_links = soup.find_all('a', href=lambda x: x and '__doPostBack' in x and 'Page$' in x)

        if not page_links:
            return False

        # Check if the next page number exists in the pagination
        next_page = current_page + 1
        for link in page_links:
            href = link.get('href', '')
            if f'Page${next_page}' in href:
                return True

        # Also check for ellipsis (...) or "Next" indicators
        # which suggest more pages exist beyond the visible range
        for link in page_links:
            text = link.get_text(strip=True)
            if text in ['...', '›', '»', 'Next', 'הבא']:  # Including Hebrew "Next"
                return True

        return False

    def fetch_page(self, page_num=None, form_data=None):
        """
        Fetch a specific page

        Args:
            page_num: Page number to fetch (None for initial page/form submission)
            form_data: Additional form data to include

        Returns:
            HTML content of the page
        """
        if page_num is None:
            if form_data:
                # Initial form POST (no pagination)
                data = {
                    '__EVENTTARGET': '',
                    '__EVENTARGUMENT': '',
                    '__LASTFOCUS': '',
                }
                # Add ViewState if available
                data.update(self.viewstate_data)
                # Add form data
                data.update(form_data)

                response = self.session.post(self.url, data=data, timeout=self.timeout)
                response.raise_for_status()
                return response.text
            else:
                # Initial GET request
                response = self.session.get(self.url, timeout=self.timeout)
                response.raise_for_status()
                return response.text
        else:
            # POST request for pagination
            data = {
                '__EVENTTARGET': 'ctl00$ContentPlaceHolder1$gvData',
                '__EVENTARGUMENT': f'Page${page_num}',
                '__LASTFOCUS': '',
            }

            # Add ViewState and other fields
            data.update(self.viewstate_data)

            # Add any additional form data
            if form_data:
                data.update(form_data)

            response = self.session.post(self.url, data=data, timeout=self.timeout)
            response.raise_for_status()
            return response.text

    def scrape_all_pages(self, initial_form_data=None):
        """
        Scrape all pages of the calendar

        Args:
            initial_form_data: Form data for the initial request (year, dates, etc.)

        Returns:
            List of HTML pages
        """
        pages = []
        current_page = 1
        previous_data_rows = None

        print("Fetching initial page...")

        # Need to GET first to get initial ViewState
        html = self.fetch_page()
        self.viewstate_data = self.extract_form_fields(html)

        # Then POST with form data to get the first page of results
        if initial_form_data:
            html = self.fetch_page(page_num=None, form_data=initial_form_data)
            self.viewstate_data = self.extract_form_fields(html)

        pages.append(html)
        previous_data_rows = self.get_data_rows(html)

        # Keep fetching pages until there's no next page
        while self.has_next_page(html, current_page):
            current_page += 1
            print(f"Fetching page {current_page}...")

            html = self.fetch_page(current_page)

            # Check if we got the same data (duplicate detection)
            # Compare actual data content, not HTML (ViewState changes every time)
            current_data_rows = self.get_data_rows(html)
            if current_data_rows == previous_data_rows:
                print(f"Detected duplicate data - stopping at page {current_page - 1}")
                break

            # Update ViewState for next request
            self.viewstate_data.update(self.extract_form_fields(html))

            pages.append(html)
            previous_data_rows = current_data_rows

            # No sleep needed - requests.Session handles connection pooling
            # and retry logic handles rate limiting if needed

        print(f"Successfully fetched {len(pages)} pages")
        return pages

    def save_pages(self, pages, output_dir='output'):
        """
        Save HTML pages to files

        Args:
            pages: List of HTML page contents
            output_dir: Directory to save pages to
        """
        import os

        if not pages:
            raise ValueError("No pages to save - scraping returned empty result")

        os.makedirs(output_dir, exist_ok=True)

        for i, page in enumerate(pages, 1):
            filename = f"{output_dir}/page_{i:03d}.html"
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(page)

        print(f"Saved {len(pages)} pages to {output_dir}/")


def load_cookies():
    """Load cookies from .cookies.json file"""
    cookies_file = Path(__file__).parent / '.cookies.json'

    if not cookies_file.exists():
        print(f"Error: {cookies_file} not found!")
        print("Run refresh_cookies.py first to generate session cookies.")
        exit(1)

    with open(cookies_file, 'r', encoding='utf-8') as f:
        return json.load(f)

def get_academic_year():
    """
    Calculate academic year based on current date.
    Academic year transitions in October (semester 1 starts).

    Examples:
        September 2025 → 2025 (still in 2024-2025 academic year)
        October 2025 → 2026 (now in 2025-2026 academic year)
        April 2026 → 2026 (still in 2025-2026 academic year)

    Returns:
        int: Academic year (e.g., 2026 for the 2025-2026 year)
    """
    now = datetime.now()
    if now.month >= ACADEMIC_YEAR_START_MONTH:
        return now.year + 1
    else:
        return now.year

def get_start_date():
    """
    Get start date for scraping.

    Fetches classes from the past SCRAPE_LOOKBACK_DAYS days to ensure
    we don't miss any recent schedule changes.

    Returns:
        str: Date in DD/MM/YYYY format (e.g., "28/10/2025")
    """
    start_date = datetime.now() - timedelta(days=SCRAPE_LOOKBACK_DAYS)
    return start_date.strftime('%d/%m/%Y')


def main():
    # Configuration
    URL = "https://live.or-bit.net/gordon/StudentScheduleList.aspx"

    # Load cookies from file
    COOKIES = load_cookies()

    # Build form data dynamically
    INITIAL_FORM_DATA = {
        'ctl00$cmbActiveYear': str(get_academic_year()),
        'ctl00$OLToolBar1$ctl03$dtFromDate$dtdtFromDate': get_start_date(),
        'ctl00$OLToolBar1$ctl03$dtToDate$dtdtToDate': '',
        'ctl00$btnOkAgreement': 'אישור'
    }

    print(f"Academic Year: {get_academic_year()}")
    print(f"Start Date: {get_start_date()}")

    # Create scraper
    scraper = CollegeCalendarScraper(URL, COOKIES)

    # Validate session before scraping
    try:
        scraper.validate_session()
    except ValueError as e:
        print(f"\nError: {e}")
        print("Session cookies are invalid. Run refresh_cookies.py to get fresh cookies.")
        exit(1)

    # Scrape all pages
    pages = scraper.scrape_all_pages(initial_form_data=INITIAL_FORM_DATA)

    # Save pages
    scraper.save_pages(pages)

    print("\nDone! You can now parse the HTML files to extract the calendar data.")


if __name__ == '__main__':
    main()
