"""Utility to sync player and team statistics from Wikipedia into local data files.

This script scrapes the 2026 FIFA World Cup Wikipedia pages and saves
structured data to the data/ directory for use as API fallback data.

Usage:
    python scripts/sync_wikipedia_data.py

Outputs:
    data/worldcup2026.players.json  — All squad players with caps/goals/position
    data/worldcup2026.team_stats.json — Team match statistics (goals scored/conceded, W/D/L)
"""

import json
import re
import sys
from pathlib import Path

import httpx
from bs4 import BeautifulSoup

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

SQUADS_URL = "https://en.wikipedia.org/wiki/2026_FIFA_World_Cup_squads"
TOURNAMENT_URL = "https://en.wikipedia.org/wiki/2026_FIFA_World_Cup"

# Mapping of Wikipedia team names to our teams CSV names
TEAM_NAME_MAP = {
    "Czech Republic": "UEFA Path D Winner",
    "Bosnia and Herzegovina": "UEFA Path A Winner",
    "Serbia": "UEFA Path C Winner",
}


def fetch_page(url: str) -> BeautifulSoup:
    """Fetch a Wikipedia page and return parsed BeautifulSoup."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
    }
    resp = httpx.get(url, headers=headers, timeout=30, follow_redirects=True)
    resp.raise_for_status()
    return BeautifulSoup(resp.text, "html.parser")


def parse_squads(soup: BeautifulSoup) -> list[dict]:
    """Parse squad tables from the Wikipedia squads page.

    Each player entry contains:
    - team: str (country name)
    - name: str
    - position: str (GK, DF, MF, FW)
    - date_of_birth: str
    - age: int
    - caps: int
    - goals: int
    - club: str
    """
    players = []
    current_team = None

    # Squad tables are organized under h3 headings with team names
    for heading in soup.find_all(["h2", "h3"]):
        # Get the heading text (team name)
        span = heading.find("span", class_="mw-headline")
        if not span:
            continue

        heading_text = span.get_text(strip=True)

        # Skip non-team headings
        if heading_text in ("References", "Notes", "Statistics", "Players",
                           "See also", "External links", "Contents"):
            continue

        # h3 headings are typically the team names within a group section
        if heading.name == "h3":
            current_team = heading_text
        elif heading.name == "h2" and "Group" not in heading_text:
            current_team = heading_text

        if not current_team:
            continue

        # Find the next table after this heading
        table = heading.find_next("table", class_="sortable")
        if not table:
            continue

        rows = table.find_all("tr")
        for row in rows[1:]:  # Skip header row
            cells = row.find_all(["td", "th"])
            if len(cells) < 7:
                continue

            try:
                # Typical columns: #, Pos, Player, DOB, Age, Caps, Goals, Club
                pos_idx = 1
                name_idx = 2
                dob_idx = 3
                age_idx = 4
                caps_idx = 5
                goals_idx = 6
                club_idx = 7 if len(cells) > 7 else -1

                position = cells[pos_idx].get_text(strip=True)
                name = cells[name_idx].get_text(strip=True)
                dob = cells[dob_idx].get_text(strip=True)

                # Parse age (remove parenthetical)
                age_text = cells[age_idx].get_text(strip=True)
                age_match = re.search(r"\d+", age_text)
                age = int(age_match.group()) if age_match else 0

                # Parse caps and goals
                caps_text = cells[caps_idx].get_text(strip=True)
                caps = int(re.sub(r"[^\d]", "", caps_text)) if caps_text else 0

                goals_text = cells[goals_idx].get_text(strip=True)
                goals = int(re.sub(r"[^\d]", "", goals_text)) if goals_text else 0

                club = cells[club_idx].get_text(strip=True) if club_idx > 0 else ""

                if name and position in ("GK", "DF", "MF", "FW"):
                    players.append({
                        "team": current_team,
                        "name": name,
                        "position": position,
                        "date_of_birth": dob,
                        "age": age,
                        "caps": caps,
                        "goals": goals,
                        "club": club,
                    })
            except (ValueError, IndexError):
                continue

    return players


def parse_team_stats(soup: BeautifulSoup) -> list[dict]:
    """Parse team match statistics from the main tournament page.

    Extracts group stage results to compute per-team stats:
    - team: str
    - matches_played: int
    - wins: int
    - draws: int
    - losses: int
    - goals_for: int
    - goals_against: int
    - goal_difference: int
    """
    teams_stats: dict[str, dict] = {}

    # Look for match result tables (group stage)
    # Match results appear in tables with score cells
    for table in soup.find_all("table", class_="wikitable"):
        rows = table.find_all("tr")
        for row in rows:
            cells = row.find_all("td")
            # Look for match result rows: Home team | Score | Away team
            if len(cells) >= 3:
                # Check if any cell contains a match score pattern (e.g. "2–0", "1–1")
                for i, cell in enumerate(cells):
                    text = cell.get_text(strip=True)
                    score_match = re.match(r"^(\d+)[–\-](\d+)$", text)
                    if score_match and i > 0 and i < len(cells) - 1:
                        home_goals = int(score_match.group(1))
                        away_goals = int(score_match.group(2))

                        # Get team names from adjacent cells
                        home_team = cells[i - 1].get_text(strip=True)
                        away_team = cells[i + 1].get_text(strip=True)

                        if not home_team or not away_team:
                            continue

                        # Initialize team entries
                        for team in [home_team, away_team]:
                            if team not in teams_stats:
                                teams_stats[team] = {
                                    "team": team,
                                    "matches_played": 0,
                                    "wins": 0,
                                    "draws": 0,
                                    "losses": 0,
                                    "goals_for": 0,
                                    "goals_against": 0,
                                }

                        # Update home team
                        teams_stats[home_team]["matches_played"] += 1
                        teams_stats[home_team]["goals_for"] += home_goals
                        teams_stats[home_team]["goals_against"] += away_goals

                        # Update away team
                        teams_stats[away_team]["matches_played"] += 1
                        teams_stats[away_team]["goals_for"] += away_goals
                        teams_stats[away_team]["goals_against"] += home_goals

                        if home_goals > away_goals:
                            teams_stats[home_team]["wins"] += 1
                            teams_stats[away_team]["losses"] += 1
                        elif home_goals < away_goals:
                            teams_stats[away_team]["wins"] += 1
                            teams_stats[home_team]["losses"] += 1
                        else:
                            teams_stats[home_team]["draws"] += 1
                            teams_stats[away_team]["draws"] += 1
                        break

    # Calculate goal difference
    for stats in teams_stats.values():
        stats["goal_difference"] = stats["goals_for"] - stats["goals_against"]

    return list(teams_stats.values())


def save_json(data: list | dict, filename: str) -> Path:
    """Save data to JSON file in the data directory."""
    filepath = DATA_DIR / filename
    filepath.parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    return filepath


def main():
    """Main sync routine."""
    print("=" * 60)
    print("  World Cup 2026 Wikipedia Data Sync")
    print("=" * 60)

    # --- Player Stats ---
    print(f"\n[1/2] Fetching squads from: {SQUADS_URL}")
    try:
        soup = fetch_page(SQUADS_URL)
        players = parse_squads(soup)
        print(f"  Parsed {len(players)} players from {len(set(p['team'] for p in players))} teams")

        filepath = save_json(players, "worldcup2026.players.json")
        print(f"  Saved to: {filepath}")
    except Exception as e:
        print(f"  ERROR fetching squads: {e}", file=sys.stderr)
        players = []

    # --- Team Stats ---
    print(f"\n[2/2] Fetching team stats from: {TOURNAMENT_URL}")
    try:
        soup = fetch_page(TOURNAMENT_URL)
        team_stats = parse_team_stats(soup)
        print(f"  Parsed stats for {len(team_stats)} teams")

        for ts in sorted(team_stats, key=lambda x: -x["matches_played"])[:10]:
            print(f"    {ts['team']}: {ts['wins']}W {ts['draws']}D {ts['losses']}L "
                  f"({ts['goals_for']}-{ts['goals_against']})")

        filepath = save_json(team_stats, "worldcup2026.team_stats.json")
        print(f"  Saved to: {filepath}")
    except Exception as e:
        print(f"  ERROR fetching team stats: {e}", file=sys.stderr)
        team_stats = []

    # Summary
    print(f"\n{'='*60}")
    print(f"  Sync complete: {len(players)} players, {len(team_stats)} teams")
    print(f"{'='*60}")

    return 0 if players and team_stats else 1


if __name__ == "__main__":
    sys.exit(main())
