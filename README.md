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

**1. Install**
```bash
uv sync
```

**2. Configure**
```bash
cp config.template.json config.json
```
Get your session cookie from browser DevTools (F12 → Network tab → `BCI_OL_KEY`)

**3. Scrape**
```bash
uv run college_calender.py
```

**4. Generate calendars**
```bash
uv run generate_ics.py --split
```

**5. Import to Google Calendar**
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

## 🛠️ Files

| File | Purpose |
|------|---------|
| `college_calender.py` | Scrape website → save HTML |
| `generate_ics.py` | Parse HTML → generate ICS |
| `config.json` | Your credentials (gitignored) |

<div align="center">

---

Made with 🤖 by Claude Code

</div>
