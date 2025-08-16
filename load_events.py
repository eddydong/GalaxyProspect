import json
import re
from datetime import datetime, timedelta
from typing import List

MONTHS = {
    'Jan': 1, 'Feb': 2, 'Mar': 3, 'Apr': 4, 'May': 5, 'Jun': 6,
    'Jul': 7, 'Aug': 8, 'Sep': 9, 'Oct': 10, 'Nov': 11, 'Dec': 12
}

def expand_date_field(date_str: str) -> List[str]:
    # Remove whitespace around semicolons
    date_str = re.sub(r'\s*;\s*', ';', date_str)
    # Split by semicolon for multi-month entries
    parts = date_str.split(';')
    all_dates = []
    year = None
    for part in parts:
        part = part.strip()
        # Find year at end
        m = re.search(r'(\d{4})$', part)
        if m:
            year = int(m.group(1))
            part = part[:m.start()].strip()
        # If year is still None, skip this part
        if year is None:
            continue
        # Find month(s)
        month_matches = list(re.finditer(r'([A-Za-z]{3})', part))
        if not month_matches:
            continue
        # If multiple months, process each
        for i, month_match in enumerate(month_matches):
            month = MONTHS[month_match.group(1)]
            # Find day(s) for this month
            if i + 1 < len(month_matches):
                days_str = part[month_match.end():month_matches[i+1].start()].strip(', -')
            else:
                days_str = part[month_match.end():].strip(', -')
            # Handle ranges (e.g., 14–16)
            for day_piece in days_str.split(','):
                day_piece = day_piece.strip()
                if not day_piece:
                    continue
                if '–' in day_piece or '-' in day_piece:
                    # Range
                    sep = '–' if '–' in day_piece else '-'
                    range_parts = [x.strip() for x in day_piece.split(sep)]
                    if len(range_parts) == 2 and range_parts[0].isdigit() and range_parts[1].isdigit():
                        start_day, end_day = int(range_parts[0]), int(range_parts[1])
                        for d in range(start_day, end_day + 1):
                            all_dates.append(f"{year:04d}-{month:02d}-{d:02d}")
                    else:
                        # Malformed range, skip
                        continue
                else:
                    # Single day
                    try:
                        d = int(day_piece)
                        all_dates.append(f"{year:04d}-{month:02d}-{d:02d}")
                    except ValueError:
                        continue
    return all_dates

def main():
    with open('events.json', 'r', encoding='utf-8') as f:
        events = json.load(f)
    expanded_events = []
    for event in events:
        date_field = event.get('date', '')
        expanded_dates = expand_date_field(date_field)
        for date in expanded_dates:
            new_event = event.copy()
            new_event['date'] = date
            expanded_events.append(new_event)
    # Output to new file
    with open('events_expanded.json', 'w', encoding='utf-8') as f:
        json.dump(expanded_events, f, ensure_ascii=False, indent=2)

if __name__ == '__main__':
    main()
