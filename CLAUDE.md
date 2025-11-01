# College classes calender importer

## GOAL
We want to have all classes to be written to my google calendar.
Ideally, I want each class to have a different color, to have its time listed in the correct date, show the "notes" )הערה) value in the google calendar event description, teacher's name, etc.

## Notes
- We'll generate an ICS file to import it to google calendar
- if 'starting time' (שעת התחלה) column's value is 00:00, ignore this class
- all classes on mondays (ב) should have the same color - yellow
- if the note column's value is 'זום' then mark it blue color
- some class names have "(ENG)" in their name, remove the '(ENG)' from the name, example: "Math (ENG)" will become "Math"
- if color is not yellow (monday) and not zoom (blue) - then make it red.
- course name: "מפילוסופיה לכיתה (מקוון סינכרוני)" is zoom, remove the parenthesis that say it's sync via zoom, and mark it blue and not yellow even that it's on monday
- if the notes don't say anthing, assume it's in college i.e. red color (unless it's on monday)
