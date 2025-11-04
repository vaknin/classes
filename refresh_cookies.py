#!/usr/bin/env python3
"""
Automated Cookie Refresh Script
Logs in to the college portal and returns fresh session cookies
"""

import requests
from bs4 import BeautifulSoup
import json
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
SCRIPT_DIR = Path(__file__).parent
COOKIES_FILE = SCRIPT_DIR / ".cookies.json"
LOGIN_URL = "https://live.or-bit.net/gordon/Login.aspx?ReturnUrl=%2fgordon%2fMain.aspx"

def get_login_page():
    """
    GET the login page to receive initial session cookie and extract form fields

    Returns:
        tuple: (session, viewstate, eventvalidation)
    """
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:144.0) Gecko/20100101 Firefox/144.0',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate, br',
    })

    print("Getting login page...")
    response = session.get(LOGIN_URL, timeout=10)
    response.raise_for_status()

    # Parse HTML to extract form fields
    soup = BeautifulSoup(response.text, 'html.parser')

    viewstate = soup.find('input', {'name': '__VIEWSTATE'})
    eventvalidation = soup.find('input', {'name': '__EVENTVALIDATION'})
    pagedatakey = soup.find('input', {'name': '__PageDataKey'})

    if not viewstate or not eventvalidation:
        raise ValueError("Could not find __VIEWSTATE or __EVENTVALIDATION in login page")

    form_fields = {
        '__VIEWSTATE': viewstate.get('value', ''),
        '__EVENTVALIDATION': eventvalidation.get('value', ''),
        '__PageDataKey': pagedatakey.get('value', '') if pagedatakey else '',
    }

    print(f"Initial session cookie: {session.cookies.get('BCI_OL_KEY', 'NOT FOUND')}")

    return session, form_fields

def login(session, form_fields, username, password):
    """
    POST login form with credentials

    Args:
        session: requests.Session with initial cookie
        form_fields: Dictionary with __VIEWSTATE, etc.
        username: Login username
        password: Login password

    Returns:
        Authenticated session with updated cookie
    """
    print("Logging in...")

    # Build form data
    form_data = {
        'ReturnUrl': '/gordon/Main.aspx',
        '__LASTFOCUS': '',
        '__EVENTTARGET': '',
        '__EVENTARGUMENT': '',
        '__PageDataKey': form_fields['__PageDataKey'],
        '__VIEWSTATE': form_fields['__VIEWSTATE'],
        '__EVENTVALIDATION': form_fields['__EVENTVALIDATION'],
        'ctl00$ContentPlaceHolder1$edtUsername': username,
        'ctl00$ContentPlaceHolder1$edtPassword': password,
        'ctl00$ContentPlaceHolder1$btnLogin': 'כניסה',
    }

    # POST login
    response = session.post(
        LOGIN_URL,
        data=form_data,
        timeout=10,
        allow_redirects=True
    )
    response.raise_for_status()

    # Check if login was successful
    if 'login' in response.url.lower():
        # Still on login page - credentials might be wrong
        soup = BeautifulSoup(response.text, 'html.parser')
        error_msg = soup.find('span', {'id': lambda x: x and 'error' in x.lower()})
        if error_msg:
            raise ValueError(f"Login failed: {error_msg.get_text(strip=True)}")
        raise ValueError("Login failed - still on login page")

    print(f"Login successful! Authenticated cookie: {session.cookies.get('BCI_OL_KEY', 'NOT FOUND')}")

    return session

def save_cookies(cookie_value):
    """
    Save cookies to .cookies.json file

    Args:
        cookie_value: BCI_OL_KEY value
    """
    print("Saving cookies...")

    cookies = {
        'BCI_OL_KEY': cookie_value,
        'OrbitLivePresentationTypeByCookie': 'GridView'
    }

    # Write to file
    with open(COOKIES_FILE, 'w', encoding='utf-8') as f:
        json.dump(cookies, f, indent=2, ensure_ascii=False)

    print(f"Cookies saved to {COOKIES_FILE}")

def main():
    """Main function to refresh cookies"""
    try:
        # Load credentials from .env
        username = os.getenv('USERNAME')
        password = os.getenv('PASSWORD')

        if not username or not password:
            print("Error: USERNAME and PASSWORD must be set in .env file")
            return 1

        print("=" * 60)
        print("Starting automated cookie refresh...")
        print("=" * 60)

        # Step 1: Get login page and initial cookie
        session, form_fields = get_login_page()

        # Step 2: Login with credentials
        session = login(session, form_fields, username, password)

        # Step 3: Extract authenticated cookie
        cookie_value = session.cookies.get('BCI_OL_KEY')
        if not cookie_value:
            print("Error: BCI_OL_KEY cookie not found after login")
            return 1

        # Step 4: Save cookies to file
        save_cookies(cookie_value)

        print("=" * 60)
        print("Cookie refresh completed successfully!")
        print("=" * 60)

        return 0

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == '__main__':
    exit(main())
