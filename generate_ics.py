#!/usr/bin/env python3
"""
Generate ICS calendar files from JSON class data
"""

from datetime import datetime, timedelta
from pathlib import Path
import json
from icalendar import Calendar, Event


class JSONLoader:
    """Load class data from JSON file"""

    def __init__(self, json_file='output/json/classes.json'):
        """
        Initialize the loader

        Args:
            json_file: Path to JSON file containing class data
        """
        self.json_file = Path(json_file)

    def load_classes(self):
        """
        Load and process classes from JSON file

        Returns:
            List of dictionaries containing class information
        """
        if not self.json_file.exists():
            print(f"No JSON file found at {self.json_file}")
            return []

        print(f"Loading classes from JSON...", end=" ", flush=True)

        with open(self.json_file, 'r', encoding='utf-8') as f:
            classes = json.load(f)

        print(f"done")
        print(f"✓ Loaded {len(classes)} classes from {self.json_file}")

        # Filter out classes with 00:00 start time
        filtered_classes = [c for c in classes if c['start_time'] != '00:00']
        removed_count = len(classes) - len(filtered_classes)

        if removed_count > 0:
            print(f"  Filtered out {removed_count} classes with 00:00 start time")

        # Parse dates and add date objects for sorting
        for class_info in filtered_classes:
            try:
                class_info['date_obj'] = datetime.strptime(class_info['date'], '%d/%m/%Y').date()
            except (ValueError, KeyError):
                # If _date_obj exists from parse_html, use it
                if '_date_obj' in class_info:
                    class_info['date_obj'] = datetime.fromisoformat(class_info['_date_obj']).date()

        return filtered_classes


class ICSGenerator:
    """Generate ICS calendar files with color coding"""

    # Google Calendar color IDs
    COLOR_BLUE = 9  # Blueberry - for Zoom classes
    COLOR_YELLOW = 5  # Banana - for Monday classes
    COLOR_RED = 11  # Tomato - for all other classes

    def __init__(self):
        """Initialize the ICS generator"""
        pass

    def assign_color(self, class_info):
        """
        Assign color to a class based on rules:
        1. Blue if course is sync online (מקוון סינכרוני) - HIGHEST PRIORITY
        2. Blue if note contains "זום"
        3. Yellow if day is "ב'" (Monday)
        4. Red for everything else

        Args:
            class_info: Dictionary with class information

        Returns:
            Color ID (integer 1-11)
        """
        # Rule 1a: Special sync online course is blue (even on Monday)
        if 'מקוון סינכרוני' in class_info['course_name']:
            return self.COLOR_BLUE

        # Rule 1b: Zoom classes are blue
        if 'זום' in class_info['note'].lower():
            return self.COLOR_BLUE

        # Rule 2: Monday classes are yellow
        if class_info['day'] == "ב'":
            return self.COLOR_YELLOW

        # Rule 3: Everything else is red
        return self.COLOR_RED

    def create_event(self, class_info):
        """
        Create an ICS event from class information

        Args:
            class_info: Dictionary with class information

        Returns:
            icalendar.Event object
        """
        event = Event()

        # Set event summary (course name) - remove "(ENG)" and sync indicators
        course_name = class_info['course_name']
        course_name = course_name.replace(' (ENG)', '').replace('(ENG)', '')
        course_name = course_name.replace(' (מקוון סינכרוני)', '').replace('(מקוון סינכרוני)', '')
        event.add('summary', course_name)

        # Parse start and end times
        start_time_str = class_info['start_time']
        end_time_str = class_info['end_time']

        start_hour, start_min = map(int, start_time_str.split(':'))
        end_hour, end_min = map(int, end_time_str.split(':'))

        # Combine date and time (use date_obj which is a date object)
        start_datetime = datetime.combine(
            class_info['date_obj'],
            datetime.min.time().replace(hour=start_hour, minute=start_min)
        )

        end_datetime = datetime.combine(
            class_info['date_obj'],
            datetime.min.time().replace(hour=end_hour, minute=end_min)
        )

        event.add('dtstart', start_datetime)
        event.add('dtend', end_datetime)

        # Set location (room)
        if class_info['room']:
            event.add('location', class_info['room'])

        # Build description with teacher and notes
        description_parts = []

        if class_info['teachers']:
            description_parts.append(f"מרצה: {class_info['teachers']}")

        if class_info['note']:
            description_parts.append(f"הערה: {class_info['note']}")

        if description_parts:
            event.add('description', '\n'.join(description_parts))

        # Assign color
        color_id = self.assign_color(class_info)

        # Add color as extended property
        # Note: Standard ICS doesn't support Google Calendar colorId directly
        # This will need to be set via Google Calendar API for proper color support
        event.add('X-GOOGLE-CALENDAR-CONTENT-COLOR', str(color_id))
        event.add('X-GOOGLE-CALENDAR-COLOR-ID', str(color_id))

        # Add color as a category for other calendar apps
        color_name = self.get_color_name(color_id)
        event.add('categories', [color_name])

        return event

    def get_color_name(self, color_id):
        """Get color name from ID"""
        color_names = {
            1: 'Lavender',
            2: 'Sage',
            3: 'Grape',
            4: 'Flamingo',
            5: 'Yellow-Monday',
            6: 'Tangerine',
            7: 'Peacock',
            8: 'Graphite',
            9: 'Blue-Zoom',
            10: 'Basil',
            11: 'Tomato'
        }
        return color_names.get(color_id, 'Default')

    def generate_calendar(self, classes, calendar_name='College Calendar', color_filter=None):
        """
        Generate ICS calendar from class list

        Args:
            classes: List of class dictionaries
            calendar_name: Name of the calendar
            color_filter: Optional color ID to filter (e.g., 9 for blue, 5 for yellow, 11 for red)

        Returns:
            icalendar.Calendar object
        """
        cal = Calendar()

        # Set calendar properties
        cal.add('prodid', '-//College Calendar Importer//EN')
        cal.add('version', '2.0')
        cal.add('X-WR-CALNAME', calendar_name)
        cal.add('X-WR-TIMEZONE', 'Asia/Jerusalem')

        # Filter classes by color if specified
        if color_filter is not None:
            filtered_classes = [
                class_info for class_info in classes
                if self.assign_color(class_info) == color_filter
            ]
        else:
            filtered_classes = classes

        # Add each class as an event
        for class_info in filtered_classes:
            event = self.create_event(class_info)
            cal.add_component(event)

        return cal

    def save_calendar(self, calendar, filename='calendar_output.ics'):
        """
        Save calendar to ICS file

        Args:
            calendar: icalendar.Calendar object
            filename: Output filename
        """
        with open(filename, 'wb') as f:
            f.write(calendar.to_ical())

        print(f"Calendar saved to {filename}")

    def print_color_summary(self):
        """Print summary of color assignments"""
        print("\n" + "="*80)
        print("Color Assignment Summary:")
        print("="*80)

        print("\nColor Rules:")
        print(f"  - Zoom classes (note contains 'זום'): Blue (ID {self.COLOR_BLUE})")
        print(f"  - Monday classes (day 'ב'): Yellow (ID {self.COLOR_YELLOW})")
        print(f"  - All other classes: Red (ID {self.COLOR_RED})")


def main():
    """Generate ICS calendar files from JSON class data"""
    import argparse

    parser_arg = argparse.ArgumentParser(description='Generate ICS calendar from JSON class data')
    parser_arg.add_argument('--test', action='store_true', help='Generate test calendar with only first class')
    parser_arg.add_argument('--output', default='calendar_output.ics', help='Output ICS filename (for single file mode)')
    parser_arg.add_argument('--split', action='store_true', help='Generate 3 separate files by color (F2F.ics, Zoom.ics, Rom.ics)')
    args = parser_arg.parse_args()

    # Load JSON file
    loader = JSONLoader()
    classes = loader.load_classes()

    if not classes:
        print("No classes found!")
        return

    # For testing, use only first class
    if args.test:
        classes = classes[:1]
        print(f"\nTest mode: Using only first class")

    generator = ICSGenerator()

    if args.split:
        # Generate 3 separate files by color
        print(f"\nGenerating ICS calendars from {len(classes)} classes...")

        # Count events by color
        print("  Categorizing classes by type...", end=" ", flush=True)
        blue_count = len([c for c in classes if generator.assign_color(c) == generator.COLOR_BLUE])
        yellow_count = len([c for c in classes if generator.assign_color(c) == generator.COLOR_YELLOW])
        red_count = len([c for c in classes if generator.assign_color(c) == generator.COLOR_RED])
        print("done")

        total_events = blue_count + yellow_count + red_count
        if total_events == 0:
            print("ERROR: No events generated! Check date range and HTML parsing.")
            print("This could mean:")
            print("  - No classes in the scraped date range")
            print("  - HTML structure has changed")
            print("  - All classes were filtered out (00:00 start time)")
            return 1

        # Blue - Zoom classes
        print(f"  Generating Zoom.ics ({blue_count} classes)...", end=" ", flush=True)
        blue_cal = generator.generate_calendar(classes, calendar_name='Zoom Classes', color_filter=generator.COLOR_BLUE)
        generator.save_calendar(blue_cal, 'Zoom.ics')
        print("done")

        # Yellow - Monday classes (Rom)
        print(f"  Generating Rom.ics ({yellow_count} classes)...", end=" ", flush=True)
        yellow_cal = generator.generate_calendar(classes, calendar_name='Rom Classes', color_filter=generator.COLOR_YELLOW)
        generator.save_calendar(yellow_cal, 'Rom.ics')
        print("done")

        # Red - F2F classes
        print(f"  Generating F2F.ics ({red_count} classes)...", end=" ", flush=True)
        red_cal = generator.generate_calendar(classes, calendar_name='F2F Classes', color_filter=generator.COLOR_RED)
        generator.save_calendar(red_cal, 'F2F.ics')
        print("done")

        print(f"\n✓ Successfully generated 3 ICS files:")
        print(f"  - Zoom.ics: {blue_count} Zoom/online classes")
        print(f"  - Rom.ics: {yellow_count} Monday classes")
        print(f"  - F2F.ics: {red_count} in-person classes")

    else:
        # Generate single file (original behavior)
        print(f"\nGenerating ICS calendar with {len(classes)} classes...")
        calendar = generator.generate_calendar(classes)

        # Save to file
        generator.save_calendar(calendar, args.output)

        # Print color summary
        generator.print_color_summary()

        print(f"\n{'='*80}")
        print(f"Success! Import {args.output} to Google Calendar to verify.")
        print('='*80)


if __name__ == '__main__':
    main()
