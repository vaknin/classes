#!/usr/bin/env python3
"""
Validate RULES.toml configuration against actual class data
Ensures all course overrides match real classes to prevent silent failures
"""

from pathlib import Path
import json

try:
    import tomllib as toml
except ImportError:
    try:
        import tomli as toml
    except ImportError:
        print("Error: 'tomli' module not found. Please install it with: pip install tomli")
        exit(1)


def validate_rules(rules_file='RULES.toml', json_file='output/json/classes.json'):
    """
    Validate that all course overrides in RULES.toml match actual classes

    Args:
        rules_file: Path to TOML rules file
        json_file: Path to JSON file containing class data

    Returns:
        True if validation passes, False otherwise
    """
    rules_path = Path(rules_file)
    json_path = Path(json_file)

    # Load RULES.toml
    if not rules_path.exists():
        print(f"Warning: {rules_file} not found. Skipping validation.")
        return True

    with open(rules_path, 'rb') as f:
        config = toml.load(f)

    # Load classes.json
    if not json_path.exists():
        print(f"Error: {json_file} not found. Cannot validate rules.")
        print(f"Run parse_html.py first to generate the JSON file.")
        return False

    with open(json_path, 'r', encoding='utf-8') as f:
        classes = json.load(f)

    # Get all class IDs and course names from actual data
    class_ids = set()
    course_names = set()

    for class_info in classes:
        if class_info.get('class_id'):
            class_ids.add(class_info['class_id'])
        if class_info.get('course_name'):
            course_names.add(class_info['course_name'])

    print(f"Validating RULES.toml against {len(classes)} classes...")
    print(f"  Found {len(class_ids)} unique class IDs")

    # Get course overrides from config
    course_overrides = config.get('courses', {})

    # Remove date_rules from course_overrides (it's validated separately)
    course_overrides_only = {k: v for k, v in course_overrides.items() if k != 'date_rules'}

    if not course_overrides_only:
        print("  No course overrides defined in RULES.toml")
    else:
        print(f"  Checking {len(course_overrides_only)} course overrides...")

        validation_errors = []

        for course_key, override in course_overrides_only.items():
            # Check if it's an exact class ID match
            if course_key in class_ids:
                print(f"  ✓ '{course_key}' - exact class ID match")
                continue

            # Check if it's a substring match for course name
            matched = False
            for course_name in course_names:
                if course_key in course_name:
                    print(f"  ✓ '{course_key}' - matches course name '{course_name}'")
                    matched = True
                    break

            if not matched:
                validation_errors.append(course_key)

        # Print results
        if validation_errors:
            print("\n" + "="*80)
            print("VALIDATION ERRORS:")
            print("="*80)
            print("\nThe following course overrides in RULES.toml do NOT match any classes:")
            for error in validation_errors:
                print(f"  ✗ '{error}'")
            print("\nPossible causes:")
            print("  - Typo in the class ID or course name")
            print("  - Class doesn't exist in the current schedule")
            print("  - Class ID format changed")
            print("\nAction required:")
            print("  - Fix the entries in RULES.toml")
            print("  - Or remove invalid entries")
            print("="*80)
            return False

    # Validate date-specific rules
    date_rules = config.get('courses', {}).get('date_rules', {})

    if date_rules:
        print(f"\n  Checking {len(date_rules)} date-specific rules...")

        date_validation_errors = []
        date_validation_warnings = []

        # Collect all dates that exist for each class
        class_dates = {}
        for class_info in classes:
            class_id = class_info.get('class_id')
            if class_id:
                if class_id not in class_dates:
                    class_dates[class_id] = set()
                class_dates[class_id].add(class_info.get('date'))

        for rule_class_id, rule_config in date_rules.items():
            # Validate class ID exists
            if rule_class_id not in class_ids:
                date_validation_errors.append(f"Class ID '{rule_class_id}' not found in data")
                continue

            print(f"  ✓ '{rule_class_id}' - validating date rules")

            # Validate include_dates if specified
            if 'include_dates' in rule_config:
                include_dates = rule_config['include_dates']

                # Check date format (DD/MM/YYYY)
                for date_str in include_dates:
                    if not isinstance(date_str, str):
                        date_validation_errors.append(f"  {rule_class_id}: date '{date_str}' is not a string")
                        continue

                    parts = date_str.split('/')
                    if len(parts) != 3 or not all(p.isdigit() for p in parts):
                        date_validation_errors.append(f"  {rule_class_id}: invalid date format '{date_str}' (expected DD/MM/YYYY)")
                    else:
                        day, month, year = parts
                        if not (1 <= int(day) <= 31 and 1 <= int(month) <= 12):
                            date_validation_errors.append(f"  {rule_class_id}: invalid date '{date_str}'")

                # Check if dates exist in actual data (warning only, not error)
                if rule_class_id in class_dates:
                    actual_dates = class_dates[rule_class_id]
                    for date_str in include_dates:
                        if date_str not in actual_dates:
                            date_validation_warnings.append(
                                f"  {rule_class_id}: date '{date_str}' not found in current data (may appear in future scrapes)"
                            )

            # Validate date-specific color configs
            if 'dates' in rule_config:
                for date_str, date_config in rule_config['dates'].items():
                    # Validate date format
                    parts = date_str.split('/')
                    if len(parts) != 3 or not all(p.isdigit() for p in parts):
                        date_validation_errors.append(f"  {rule_class_id}: invalid date format '{date_str}' in dates config")

                    # Validate color if specified
                    if 'color' in date_config:
                        color = date_config['color']
                        valid_colors = list(config.get('colors', {}).keys()) + list(range(1, 12))
                        if color not in valid_colors:
                            date_validation_errors.append(f"  {rule_class_id}: invalid color '{color}' for date '{date_str}'")

        # Print warnings
        if date_validation_warnings:
            print("\n" + "="*80)
            print("VALIDATION WARNINGS:")
            print("="*80)
            print("\nThe following dates in RULES.toml don't exist in current data:")
            for warning in date_validation_warnings:
                print(f"  ⚠ {warning}")
            print("\nThis is OK if these dates will appear in future scrapes.")
            print("="*80)

        # Print errors
        if date_validation_errors:
            print("\n" + "="*80)
            print("DATE RULES VALIDATION ERRORS:")
            print("="*80)
            print("\nThe following date rules in RULES.toml have errors:")
            for error in date_validation_errors:
                print(f"  ✗ {error}")
            print("\nAction required:")
            print("  - Fix the date format (use DD/MM/YYYY)")
            print("  - Verify class IDs are correct")
            print("  - Check color names/IDs are valid")
            print("="*80)
            return False

    print("\n✓ All course overrides in RULES.toml are valid!")
    return True


def main():
    """Run validation"""
    if not validate_rules():
        exit(1)
    exit(0)


if __name__ == '__main__':
    main()
