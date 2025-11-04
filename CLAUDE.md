# College Calendar Automation System

## GOAL
Automatically scrape college class schedules and sync them to Google Calendar with color-coded categories.

## System Architecture

### Automation Flow
1. **Auto-login**: `refresh_cookies.py` logs in using credentials from `.env`
2. **Scrape**: `college_calender.py` fetches all calendar pages with dynamic date calculation
3. **Generate ICS**: `generate_ics.py` creates 3 separate ICS files by category
4. **Sync to GitHub**: `run_pipeline.sh` commits and pushes changes
5. **Scheduled**: systemd timer runs weekly (Saturday 3 AM)

### Configuration
- **Credentials**: Stored in `.env` (USERNAME, PASSWORD)
- **Academic Year**: Auto-calculated (if month >= October: year+1, else year)
- **Date Range**: Automatically fetches last 7 days of classes
- **No manual config needed** - everything is automated

## ICS Generation Rules

### Color Categories (3 separate files)
- **Blue (Zoom.ics)**: Online/Zoom classes
  - Note contains 'זום'
  - Course name contains 'מקוון סינכרוני'
- **Yellow (Rom.ics)**: Monday classes
  - Day is 'ב' (Monday)
  - Unless it's a Zoom class (blue takes priority)
- **Red (F2F.ics)**: In-person classes
  - Everything else (default)

### Data Processing
- **Filter**: Ignore classes with start time 00:00
- **Clean names**: Remove "(ENG)" and "(מקוון סינכרוני)" from course names
- **Include**: Teacher name and notes in event description
- **Location**: Room number as event location

## Files

### Core Scripts
- `refresh_cookies.py` - Auto-login and session management
- `college_calender.py` - Web scraper with ASP.NET ViewState handling
- `generate_ics.py` - ICS file generator with color coding
- `run_pipeline.sh` - Main automation orchestrator

### Configuration
- `.env` - Login credentials (gitignored)
- `.cookies.json` - Session cookies (auto-generated, gitignored)
- `systemd/*.{service,timer}` - Weekly automation

### Output
- `output/page_*.html` - Raw HTML pages (gitignored)
- `F2F.ics`, `Zoom.ics`, `Rom.ics` - Calendar files (committed to git)
