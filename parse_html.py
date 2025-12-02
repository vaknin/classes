#!/usr/bin/env python3
"""
Parse HTML files and convert to JSON format
Converts scraped HTML pages to a structured JSON format for easier processing
"""

from bs4 import BeautifulSoup
from pathlib import Path
import json
from datetime import datetime


class HTMLToJSONParser:
    """Parse HTML pages and extract class data to JSON"""

    def __init__(self, input_dir='output/html', output_dir='output/json'):
        """
        Initialize the parser

        Args:
            input_dir: Directory containing scraped HTML pages
            output_dir: Directory to save JSON output
        """
        self.input_dir = Path(input_dir)
        self.output_dir = Path(output_dir)

    def parse_all_pages(self):
        """
        Parse all HTML pages and extract class data

        Returns:
            List of class dictionaries
        """
        all_classes = []

        # Find all HTML files in input directory
        html_files = sorted(self.input_dir.glob('page_*.html'))

        if not html_files:
            print(f"No HTML files found in {self.input_dir}/")
            return []

        print(f"Parsing {len(html_files)} HTML files...")

        for i, html_file in enumerate(html_files, 1):
            classes = self.parse_page(html_file)
            all_classes.extend(classes)
            if i % 5 == 0 or i == len(html_files):
                print(f"  Processed {i}/{len(html_files)} files ({len(all_classes)} classes so far)")

        print(f"✓ Total classes extracted: {len(all_classes)}")

        return all_classes

    def parse_page(self, html_file):
        """
        Parse a single HTML page and extract classes

        Args:
            html_file: Path to HTML file

        Returns:
            List of class dictionaries with 8 fields
        """
        with open(html_file, 'r', encoding='utf-8') as f:
            html = f.read()

        soup = BeautifulSoup(html, 'html.parser')

        # Find the data table
        table = soup.find('table', {'id': 'ContentPlaceHolder1_gvData'})

        if not table:
            return []

        classes = []

        # Get all rows except the header (first row)
        rows = table.find_all('tr', class_='GridRow')

        for row in rows:
            cells = row.find_all('td')

            if len(cells) < 8:
                continue

            # Extract text from each cell - 8 fields exactly as they appear in HTML
            date_str = cells[0].get_text(strip=True)           # תאריך
            day = cells[1].get_text(strip=True)                # יום
            start_time = cells[2].get_text(strip=True)         # שעת התחלה
            end_time = cells[3].get_text(strip=True)           # שעת סיום
            course_name = cells[4].get_text(strip=True)        # שם
            teachers = cells[5].get_text(strip=True)           # מרצים
            room = cells[6].get_text(strip=True)               # חדר
            note = cells[7].get_text(strip=True)               # הערה

            # Skip empty rows
            if not date_str or not start_time:
                continue

            # Parse date (DD/MM/YYYY format)
            try:
                date_obj = datetime.strptime(date_str, '%d/%m/%Y').date()
            except ValueError:
                print(f"Warning: Could not parse date '{date_str}'")
                continue

            # Create class dictionary with all 8 fields
            class_info = {
                'date': date_str,              # תאריך (keep as string for JSON)
                'day': day,                    # יום
                'start_time': start_time,      # שעת התחלה
                'end_time': end_time,          # שעת סיום
                'course_name': course_name,    # שם
                'teachers': teachers,          # מרצים
                'room': room,                  # חדר
                'note': note,                  # הערה
                '_date_obj': date_obj.isoformat(),  # ISO date for sorting
            }

            classes.append(class_info)

        return classes

    def save_json(self, classes, filename='classes.json'):
        """
        Save classes to JSON file

        Args:
            classes: List of class dictionaries
            filename: Output filename
        """
        self.output_dir.mkdir(parents=True, exist_ok=True)

        output_file = self.output_dir / filename

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(classes, f, ensure_ascii=False, indent=2)

        print(f"✓ Saved {len(classes)} classes to {output_file}")

        return output_file


def main():
    """Parse HTML files and save to JSON"""
    parser = HTMLToJSONParser()

    # Parse all HTML pages
    classes = parser.parse_all_pages()

    if not classes:
        print("No classes found!")
        return 1

    # Save to JSON
    parser.save_json(classes)

    print(f"\n✓ Done! JSON file ready for ICS generation")
    return 0


if __name__ == '__main__':
    exit(main())
