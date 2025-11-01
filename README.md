# College Calendar Scraper

Automated scraper for fetching your college's calendar from ASP.NET-based websites that don't provide downloadable versions.

## Features

- Handles ASP.NET ViewState and session management
- Automatically paginates through all pages
- Saves HTML pages for later parsing
- Uses secure cookie-based authentication

## Setup

1. **Install dependencies**:
   ```bash
   uv sync
   ```

2. **Create your config file**:
   ```bash
   cp config.template.json config.json
   ```

3. **Get your session cookies**:
   - Open your browser and log into your college portal
   - Navigate to the calendar/schedule page
   - Open Developer Tools (F12)
   - Go to the Network tab
   - Refresh the page or click on a pagination link
   - Find the request to `StudentScheduleList.aspx`
   - Look for the Cookie header in the request
   - Copy the `BCI_OL_KEY` value

4. **Update config.json**:
   ```json
   {
     "url": "https://live.or-bit.net/gordon/StudentScheduleList.aspx",
     "cookies": {
       "BCI_OL_KEY": "paste_your_actual_key_here",
       "OrbitLivePresentationTypeByCookie": "GridView"
     },
     "form_data": {
       "ctl00$cmbActiveYear": "2026",
       "ctl00$OLToolBar1$ctl03$dtFromDate$dtdtFromDate": "01/11/2025",
       "ctl00$OLToolBar1$ctl03$dtToDate$dtdtToDate": "",
       "ctl00$btnOkAgreement": "אישור"
     }
   }
   ```

## Usage

Run the scraper:
```bash
uv run college_calender.py
```

The script will:
1. Connect to your college portal using your session cookies
2. Fetch the first page to determine total page count
3. Iterate through all pages
4. Save each page as HTML in the `output/` directory

## Output

HTML files are saved in `output/page_001.html`, `output/page_002.html`, etc.

## Troubleshooting

### "Config not found" error
Make sure you've created `config.json` from the template.

### "Please update config.json" error
You need to replace `YOUR_SESSION_KEY_HERE` with your actual `BCI_OL_KEY` cookie value.

### Authentication errors
Your session cookies may have expired. Log in again and get fresh cookies from the Network tab.

### No pages found
Check that the form_data in config.json matches the expected format for your college's system.

## Notes

- Session cookies expire after a period of inactivity. You'll need to refresh them periodically.
- The scraper adds a 0.5 second delay between page requests to be respectful to the server.
- The `config.json` file is gitignored to protect your credentials.

## Next Steps

Once you have the HTML files, you can:
1. Parse them to extract calendar events
2. Convert to ICS format for importing into Google Calendar
3. Export as CSV for spreadsheet analysis
4. Generate PDF reports
