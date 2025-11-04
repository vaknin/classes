<div align="center">

# 📅 College Calendar Importer

*Automatically scrape & import your college schedule to Google Calendar*

---

### 🎯 What it does

Scrapes your college's ASP.NET calendar → Generates color-coded ICS files → Import to Google Calendar

**🔵 Blue** for Zoom classes • **🟡 Yellow** for Mondays • **🔴 Red** for in-person

---

</div>

## ⚡ Quick Start

**1. Install dependencies**
```bash
uv sync
```

**2. Configure credentials**
Create a `.env` file with your college portal login:
```bash
cp .env.example .env
# Edit .env with your username and password
```

**3. Run the pipeline**
```bash
# Test run (no git operations)
./run_pipeline.sh --dry-run

# Full run (scrape + generate + commit + push)
./run_pipeline.sh
```

The pipeline automatically:
- ✅ Logs in and refreshes session cookies
- ✅ Scrapes all calendar pages (dynamic date calculation)
- ✅ Generates 3 color-coded ICS files
- ✅ Commits and pushes to GitHub

**4. Import to Google Calendar**
- Create 3 calendars: "Zoom", "Rom", "F2F"
- Import each ICS file to its calendar
- Set colors: Blue, Yellow, Red

<div align="center">

---

✨ **227 classes** • **3 calendars** • **0 manual work** ✨

</div>

## 📂 What you get

```
F2F.ics   → 99 in-person classes (Red)
Zoom.ics  → 96 online classes (Blue)
Rom.ics   → 32 Monday classes (Yellow)
```

## 🎨 Smart Color Rules

- 🔵 Zoom classes (note contains "זום")
- 🔵 Sync online courses (even on Monday)
- 🟡 Monday classes (ב')
- 🔴 Everything else

## 🤖 Automated Updates (systemd)

Run the entire pipeline automatically every week:

**1. Install systemd files**
```bash
mkdir -p ~/.config/systemd/user
cp systemd/college-calendar.{service,timer} ~/.config/systemd/user/
```

**2. Enable and start the timer**
```bash
systemctl --user enable college-calendar.timer
systemctl --user start college-calendar.timer
```

**3. Check status**
```bash
systemctl --user list-timers college-calendar.timer
```

The timer runs every **Saturday at 3:00 AM** (with 0-5 min random delay) and will catch up if your computer was off (Persistent=true).

### 🔍 Useful Commands

```bash
# View logs
journalctl --user -u college-calendar.service -f

# Run manually now
systemctl --user start college-calendar.service

# Stop/disable timer
systemctl --user stop college-calendar.timer
systemctl --user disable college-calendar.timer
```

## 🛠️ Files

| File | Purpose |
|------|---------|
| `refresh_cookies.py` | Auto-login and session management |
| `college_calender.py` | Scrape website → save HTML |
| `generate_ics.py` | Parse HTML → generate ICS |
| `run_pipeline.sh` | Full automation orchestrator |
| `.env` | Your credentials (gitignored) |
| `.cookies.json` | Session cookies (auto-generated, gitignored) |
| `systemd/*.service` | Systemd service definition |
| `systemd/*.timer` | Weekly schedule timer |

<div align="center">

---

Made with 🤖 by Claude Code

</div>
