"""Fix stadium assignments for June 14 matches based on verified FIFA/Wikipedia data."""
import csv

rows = list(csv.DictReader(open('data/worldcup2026.games.csv', encoding='utf-8')))
fieldnames = list(rows[0].keys())

# Correct stadium_ids for June 14 matches (verified from Wikipedia):
# Match 9 (Ivory Coast vs Ecuador): Lincoln Financial Field, Philadelphia = stadium_id 10
# Match 10 (Germany vs Curacao): NRG Stadium, Houston = stadium_id 5
# Match 11 (Netherlands vs Japan): AT&T Stadium, Arlington = stadium_id 4
# Match 12 (Sweden vs Tunisia): Estadio BBVA, Guadalupe = stadium_id 3
fixes = {'9': '10', '10': '5', '11': '4', '12': '3'}

for row in rows:
    if row['id'] in fixes:
        row['stadium_id'] = fixes[row['id']]

with open('data/worldcup2026.games.csv', 'w', encoding='utf-8', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)

print('Fixed stadium assignments:')
for row in rows:
    if row['id'] in fixes:
        print(f"  Match {row['id']}: stadium_id={row['stadium_id']}")
