#!/usr/bin/env python3
"""
Parse college calendar HTML files and extract class data
"""

import os
from datetime import datetime
from bs4 import BeautifulSoup
from pathlib import Path


class CalendarParser:
    """Parse HTML calendar pages and extract class information"""

    def __init__(self, output_dir='output'):
        """
        Initialize the parser

        Args:
            output_dir: Directory containing the scraped HTML pages
        """
        self.output_dir = Path(output_dir)

    def parse_all_pages(self):
        """
        Parse all HTML pages and extract class data

        Returns:
            List of dictionaries containing class information
        """
        all_classes = []

        # Find all HTML files in output directory
        html_files = sorted(self.output_dir.glob('page_*.html'))

        if not html_files:
            print(f"No HTML files found in {self.output_dir}/")
            return []

        print(f"Found {len(html_files)} HTML files to parse")

        for html_file in html_files:
            classes = self.parse_page(html_file)
            all_classes.extend(classes)
            print(f"Parsed {html_file.name}: {len(classes)} classes")

        print(f"\nTotal classes extracted: {len(all_classes)}")

        # Filter out classes with 00:00 start time
        filtered_classes = [c for c in all_classes if c['start_time'] != '00:00']
        removed_count = len(all_classes) - len(filtered_classes)

        if removed_count > 0:
            print(f"Filtered out {removed_count} classes with 00:00 start time")

        return filtered_classes

    def parse_page(self, html_file):
        """
        Parse a single HTML page and extract classes

        Args:
            html_file: Path to HTML file

        Returns:
            List of class dictionaries
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

            # Extract text from each cell
            date_str = cells[0].get_text(strip=True)
            day = cells[1].get_text(strip=True)
            start_time = cells[2].get_text(strip=True)
            end_time = cells[3].get_text(strip=True)
            course_name = cells[4].get_text(strip=True)
            teachers = cells[5].get_text(strip=True)
            room = cells[6].get_text(strip=True)
            note = cells[7].get_text(strip=True)

            # Skip empty rows
            if not date_str or not start_time:
                continue

            # Parse date (DD/MM/YYYY format)
            try:
                date_obj = datetime.strptime(date_str, '%d/%m/%Y').date()
            except ValueError:
                print(f"Warning: Could not parse date '{date_str}'")
                continue

            # Create class dictionary
            class_info = {
                'date': date_obj,
                'date_str': date_str,
                'day': day,
                'start_time': start_time,
                'end_time': end_time,
                'course_name': course_name,
                'teachers': teachers,
                'room': room,
                'note': note,
            }

            classes.append(class_info)

        return classes


def main():
    """Test the parser"""
    parser = CalendarParser()
    classes = parser.parse_all_pages()

    print(f"\n{'='*80}")
    print("Sample classes:")
    print('='*80)

    # Show first 5 classes
    for i, cls in enumerate(classes[:5], 1):
        print(f"\n{i}. {cls['course_name']}")
        print(f"   Date: {cls['date_str']} ({cls['day']})")
        print(f"   Time: {cls['start_time']} - {cls['end_time']}")
        print(f"   Teacher: {cls['teachers']}")
        print(f"   Room: {cls['room']}")
        if cls['note']:
            print(f"   Note: {cls['note']}")


if __name__ == '__main__':
    main()
