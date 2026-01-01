#!/usr/bin/env python3
"""
Generate ICS calendar files from JSON class data
"""

from datetime import datetime, timedelta
from pathlib import Path
import json
from icalendar import Calendar, Event

# Try to import tomllib (Python 3.11+) or tomli
try:
    import tomllib as toml
except ImportError:
    try:
        import tomli as toml
    except ImportError:
        print("Error: 'tomli' module not found. Please install it with: pip install tomli")
        exit(1)


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

    def __init__(self, rules_file='RULES.toml'):
        """
        Initialize the ICS generator and load rules

        Args:
            rules_file: Path to TOML rules file
        """
        self.rules_file = Path(rules_file)
        self.config = self.load_rules()
        self.colors = self.config.get('colors', {})
        self.rules = self.config.get('rules', [])
        self.course_overrides = self.config.get('courses', {})
        
        # Default colors if not specified
        if not self.colors:
            self.colors = {
                'blue': 9,
                'yellow': 5,
                'red': 11
            }

    def load_rules(self):
        """Load rules from TOML file"""
        if not self.rules_file.exists():
            print(f"Warning: {self.rules_file} not found. Using default hardcoded rules.")
            return {
                'defaults': {'default_color': 11},
                'colors': {'blue': 9, 'yellow': 5, 'red': 11},
                'rules': [
                    {'name': 'Sync Online', 'condition': "'מקוון סינכרוני' in course_name", 'color': 'blue'},
                    {'name': 'Zoom Note', 'condition': "'זום' in note.lower()", 'color': 'blue'},
                    {'name': 'Monday Class', 'condition': "day == \"ב'\"", 'color': 'yellow'}
                ]
            }
        
        try:
            with open(self.rules_file, 'rb') as f:
                return toml.load(f)
        except Exception as e:
            print(f"Error loading {self.rules_file}: {e}")
            exit(1)

    def get_color_id(self, color_name_or_id):
        """Resolve color name to ID"""
        if isinstance(color_name_or_id, int):
            return color_name_or_id
        
        # Try to look up name in colors map
        if str(color_name_or_id) in self.colors:
            return self.colors[str(color_name_or_id)]
            
        # If it's a digit string, return as int
        if str(color_name_or_id).isdigit():
            return int(color_name_or_id)
            
        # Default fallback
        return self.config.get('defaults', {}).get('default_color', 11)

    def assign_color(self, class_info):
        """
        Assign color to a class based on rules from TOML
        Priority: date-specific color > course override > rules > default

        Args:
            class_info: Dictionary with class information

        Returns:
            Color ID (integer 1-11)
        """
        # Prepare variables for eval context
        context = {
            'course_name': class_info.get('course_name', ''),
            'class_id': class_info.get('class_id', ''),
            'note': class_info.get('note', ''),
            'day': class_info.get('day', ''),
            'room': class_info.get('room', ''),
            'teachers': class_info.get('teachers', '')
        }

        # Check date-specific color rules first (highest priority)
        date_rules = self.config.get('courses', {}).get('date_rules', {})
        if context['class_id'] and str(context['class_id']) in date_rules:
            rule = date_rules[str(context['class_id'])]
            class_date = class_info.get('date')  # DD/MM/YYYY format

            # Check if there's a color override for this specific date
            if 'dates' in rule and class_date in rule['dates']:
                date_config = rule['dates'][class_date]
                if 'color' in date_config:
                    return self.get_color_id(date_config['color'])

        # Check course overrides (optional color override)
        # Check by ID first (exact match)
        if context['class_id'] and str(context['class_id']) in self.course_overrides:
            override = self.course_overrides[str(context['class_id'])]
            if 'color' in override:
                return self.get_color_id(override['color'])

        # Check by Name (substring)
        for course_key, override in self.course_overrides.items():
            if course_key in context['course_name']:
                if 'color' in override:
                    return self.get_color_id(override['color'])

        # Evaluate rules in order
        for rule in self.rules:
            try:
                condition = rule.get('condition', 'False')
                if eval(condition, {}, context):
                    return self.get_color_id(rule.get('color'))
            except Exception as e:
                print(f"Warning: Error evaluating rule '{rule.get('name')}': {e}")
                continue

        # Default color
        return self.get_color_id(self.config.get('defaults', {}).get('default_color', 11))

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

        if class_info.get('class_id'):
             description_parts.append(f"מזהה קורס: {class_info['class_id']}")

        if class_info['teachers']:
            description_parts.append(f"מרצה: {class_info['teachers']}")

        if class_info['note']:
            description_parts.append(f"הערה: {class_info['note']}")
            
        # Check for course overrides (links and extra descriptions)
        # Check by ID first
        class_id = class_info.get('class_id')
        override_found = False
        
        if class_id and str(class_id) in self.course_overrides:
            override = self.course_overrides[str(class_id)]
            if 'link' in override:
                description_parts.append(f"Zoom Link: {override['link']}")
            if 'description' in override:
                description_parts.append(f"{override['description']}")
            override_found = True
            
        # Check by Name (substring) if not found by ID (or should we allow both?)
        # Let's allow both, but maybe avoid duplicates if they map to same
        if not override_found:
            for course_key, override in self.course_overrides.items():
                if course_key in class_info['course_name']:
                    if 'link' in override:
                        description_parts.append(f"Zoom Link: {override['link']}")
                    
                    if 'description' in override:
                        description_parts.append(f"{override['description']}")

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
        # Reverse lookup from colors dict
        for name, cid in self.colors.items():
            if cid == color_id:
                return name.capitalize()
        return 'Default'

    def should_include_class(self, class_info):
        """
        Check if a class should be included based on date filtering rules

        Args:
            class_info: Dictionary with class information

        Returns:
            True if class should be included, False to filter it out
        """
        class_id = class_info.get('class_id')
        if not class_id:
            return True

        # Check if there's a date rule for this class
        date_rules = self.config.get('courses', {}).get('date_rules', {})

        # Check by exact class ID match
        if str(class_id) in date_rules:
            rule = date_rules[str(class_id)]
            if 'include_dates' in rule:
                # If include_dates list is specified, only include classes on those dates
                allowed_dates = rule['include_dates']
                class_date = class_info.get('date')  # DD/MM/YYYY format
                return class_date in allowed_dates

        # No date restrictions, include the class
        return True

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

        # Filter classes by date restrictions first
        date_filtered_classes = [
            class_info for class_info in classes
            if self.should_include_class(class_info)
        ]

        # Then filter by color if specified
        if color_filter is not None:
            filtered_classes = [
                class_info for class_info in date_filtered_classes
                if self.assign_color(class_info) == color_filter
            ]
        else:
            filtered_classes = date_filtered_classes

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

        print("\nActive Rules (from RULES.toml):")
        for rule in self.rules:
            print(f"  - {rule.get('name')}: {rule.get('color')}")
            
        print("\nCourse Overrides:")
        for course, override in self.course_overrides.items():
            print(f"  - {course}: {override}")


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
        
        # Get configured colors for splitting
        # We need to know which colors map to which files
        # This is a bit tricky with dynamic rules, so we'll stick to the original 3 categories for now
        # or we could make this configurable too.
        # For now, let's assume the standard 3: Blue (Zoom), Yellow (Rom), Red (F2F)
        
        blue_id = generator.get_color_id('blue')
        yellow_id = generator.get_color_id('yellow')
        red_id = generator.get_color_id('red')

        # Count events by color
        print("  Categorizing classes by type...", end=" ", flush=True)
        blue_count = len([c for c in classes if generator.assign_color(c) == blue_id])
        yellow_count = len([c for c in classes if generator.assign_color(c) == yellow_id])
        red_count = len([c for c in classes if generator.assign_color(c) == red_id])
        
        # Count others?
        other_count = len([c for c in classes if generator.assign_color(c) not in [blue_id, yellow_id, red_id]])
        
        print("done")

        total_events = blue_count + yellow_count + red_count + other_count
        if total_events == 0:
            print("ERROR: No events generated! Check date range and HTML parsing.")
            return 1

        # Blue - Zoom classes
        print(f"  Generating Zoom.ics ({blue_count} classes)...", end=" ", flush=True)
        blue_cal = generator.generate_calendar(classes, calendar_name='Zoom Classes', color_filter=blue_id)
        generator.save_calendar(blue_cal, 'Zoom.ics')
        print("done")

        # Yellow - Monday classes (Rom)
        print(f"  Generating Rom.ics ({yellow_count} classes)...", end=" ", flush=True)
        yellow_cal = generator.generate_calendar(classes, calendar_name='Rom Classes', color_filter=yellow_id)
        generator.save_calendar(yellow_cal, 'Rom.ics')
        print("done")

        # Red - F2F classes
        print(f"  Generating F2F.ics ({red_count} classes)...", end=" ", flush=True)
        red_cal = generator.generate_calendar(classes, calendar_name='F2F Classes', color_filter=red_id)
        generator.save_calendar(red_cal, 'F2F.ics')
        print("done")
        
        if other_count > 0:
             print(f"  Generating Other.ics ({other_count} classes)...", end=" ", flush=True)
             # Filter for anything not in the main 3
             other_cal = Calendar()
             other_cal.add('prodid', '-//College Calendar Importer//EN')
             other_cal.add('version', '2.0')
             other_cal.add('X-WR-CALNAME', 'Other Classes')
             
             for class_info in classes:
                 cid = generator.assign_color(class_info)
                 if cid not in [blue_id, yellow_id, red_id]:
                     event = generator.create_event(class_info)
                     other_cal.add_component(event)
                     
             generator.save_calendar(other_cal, 'Other.ics')
             print("done")

        print(f"\n✓ Successfully generated ICS files:")
        print(f"  - Zoom.ics: {blue_count} Zoom/online classes")
        print(f"  - Rom.ics: {yellow_count} Monday classes")
        print(f"  - F2F.ics: {red_count} in-person classes")
        if other_count > 0:
            print(f"  - Other.ics: {other_count} other classes")

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
