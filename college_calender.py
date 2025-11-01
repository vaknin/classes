#!/usr/bin/env python3
"""
College Calendar Scraper for ASP.NET WebForms
Handles ViewState and pagination to fetch all class schedules
"""

import requests
from bs4 import BeautifulSoup
import json
import time
from urllib.parse import unquote

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

                response = self.session.post(self.url, data=data)
                response.raise_for_status()
                return response.text
            else:
                # Initial GET request
                response = self.session.get(self.url)
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

            response = self.session.post(self.url, data=data)
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

            # Be nice to the server
            time.sleep(0.5)

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

        os.makedirs(output_dir, exist_ok=True)

        for i, page in enumerate(pages, 1):
            filename = f"{output_dir}/page_{i:03d}.html"
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(page)

        print(f"Saved {len(pages)} pages to {output_dir}/")


def load_config(config_path='config.json'):
    """Load configuration from JSON file"""
    import os

    if not os.path.exists(config_path):
        print(f"Error: {config_path} not found!")
        print("Please copy config.template.json to config.json and fill in your credentials.")
        exit(1)

    with open(config_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def main():
    # Load configuration
    config = load_config()

    URL = config['url']
    COOKIES = config['cookies']
    INITIAL_FORM_DATA = config.get('form_data', None)

    # Validate cookies
    if COOKIES.get('BCI_OL_KEY') == 'YOUR_SESSION_KEY_HERE':
        print("Error: Please update config.json with your actual session cookies!")
        print("You can find these in your browser's Network tab.")
        exit(1)

    # Create scraper
    scraper = CollegeCalendarScraper(URL, COOKIES)

    # Scrape all pages
    pages = scraper.scrape_all_pages(initial_form_data=INITIAL_FORM_DATA)

    # Save pages
    scraper.save_pages(pages)

    print("\nDone! You can now parse the HTML files to extract the calendar data.")


if __name__ == '__main__':
    main()
