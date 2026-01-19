# config/semantic_patterns.py
"""
Enhanced Semantic Layer Patterns for NCAA Basketball Analytics

This module defines 30+ pre-verified SQL patterns for common basketball questions.
Each pattern includes:
- Regex patterns for question matching
- SQL template with placeholders
- Response formatting function
- Confidence scoring

The goal is to provide a fair comparison against the Visual Context agent
by covering a comprehensive set of analytical questions.
"""

import re
import sqlite3
from dataclasses import dataclass, field
from typing import Callable, Optional
from pathlib import Path


@dataclass
class SemanticPattern:
    """Definition of a semantic query pattern."""
    
    name: str
    description: str
    patterns: list[str]  # Regex patterns to match
    sql_template: str    # SQL with {game_id} and other placeholders
    format_template: str  # String template with {field} placeholders
    
    # Optional constraints
    min_confidence: float = 0.9
    requires_game_context: bool = True
    category: str = "general"
    
    def format_result(self, row: dict) -> str:
        """Format a database row into a human-readable answer."""
        try:
            return self.format_template.format(**row)
        except KeyError as e:
            return f"Result: {row}"


# =============================================================================
# TEAM NAME ALIASES
# =============================================================================
# Map common team references to database values

TEAM_ALIASES = {
    # ACC
    "duke": ["duke", "blue devils"],
    "wake forest": ["wake", "wake forest", "demon deacons"],
    "north carolina": ["unc", "carolina", "tar heels", "north carolina"],
    "virginia": ["uva", "virginia", "cavaliers", "wahoos"],
    "nc state": ["nc state", "wolfpack", "north carolina state"],
    "clemson": ["clemson", "tigers"],
    "louisville": ["louisville", "cardinals"],
    "syracuse": ["syracuse", "orange"],
    "pittsburgh": ["pitt", "pittsburgh", "panthers"],
    "boston college": ["bc", "boston college", "eagles"],
    "miami": ["miami", "hurricanes"],
    "georgia tech": ["georgia tech", "gt", "yellow jackets"],
    "notre dame": ["notre dame", "irish", "fighting irish"],
    "florida state": ["florida state", "fsu", "seminoles"],
    
    # Big 12 (new additions)
    "texas": ["texas", "longhorns", "ut"],
    "byu": ["byu", "cougars", "brigham young"],
    "utah": ["utah", "utes"],
    "colorado": ["colorado", "buffaloes", "buffs", "cu"],
    "arizona": ["arizona", "wildcats", "zona"],
    "arizona state": ["arizona state", "asu", "sun devils"],
    "tcu": ["tcu", "horned frogs"],
    "baylor": ["baylor", "bears"],
    "kansas": ["kansas", "jayhawks", "ku"],
    "kansas state": ["kansas state", "k-state", "wildcats"],
    "oklahoma state": ["oklahoma state", "okst", "cowboys"],
    "iowa state": ["iowa state", "isu", "cyclones"],
    "west virginia": ["west virginia", "wvu", "mountaineers"],
    "texas tech": ["texas tech", "ttu", "red raiders"],
    "cincinnati": ["cincinnati", "bearcats"],
    "houston": ["houston", "cougars", "uh"],
    "ucf": ["ucf", "knights", "central florida"],
    
    # SEC
    "alabama": ["alabama", "bama", "crimson tide"],
    "auburn": ["auburn", "tigers"],
    "arkansas": ["arkansas", "razorbacks", "hogs"],
    "tennessee": ["tennessee", "vols", "volunteers"],
    "kentucky": ["kentucky", "uk", "wildcats"],
    "florida": ["florida", "gators", "uf"],
    "georgia": ["georgia", "uga", "bulldogs"],
    "south carolina": ["south carolina", "gamecocks", "sc"],
    "lsu": ["lsu", "tigers", "louisiana state"],
    "mississippi state": ["mississippi state", "miss state", "bulldogs"],
    "ole miss": ["ole miss", "rebels", "mississippi"],
    "missouri": ["missouri", "mizzou", "tigers"],
    "vanderbilt": ["vanderbilt", "vandy", "commodores"],
    "texas a&m": ["texas a&m", "tamu", "aggies"],
    
    # Big Ten
    "purdue": ["purdue", "boilermakers"],
    "indiana": ["indiana", "hoosiers", "iu"],
    "michigan": ["michigan", "wolverines"],
    "michigan state": ["michigan state", "msu", "spartans"],
    "ohio state": ["ohio state", "osu", "buckeyes"],
    "illinois": ["illinois", "illini"],
    "iowa": ["iowa", "hawkeyes"],
    "wisconsin": ["wisconsin", "badgers"],
    "minnesota": ["minnesota", "gophers", "golden gophers"],
    "northwestern": ["northwestern", "wildcats"],
    "penn state": ["penn state", "psu", "nittany lions"],
    "maryland": ["maryland", "terrapins", "terps"],
    "nebraska": ["nebraska", "cornhuskers", "huskers"],
    "rutgers": ["rutgers", "scarlet knights"],
    
    # Other notable
    "gonzaga": ["gonzaga", "zags", "bulldogs"],
    "uconn": ["uconn", "connecticut", "huskies"],
    "villanova": ["villanova", "nova", "wildcats"],
    "creighton": ["creighton", "bluejays"],
    "marquette": ["marquette", "golden eagles"],
    "stanford": ["stanford", "cardinal"],
    "ucla": ["ucla", "bruins"],
    "usc": ["usc", "trojans", "southern cal"],
    "oregon": ["oregon", "ducks"],
    "smu": ["smu", "mustangs"],
}


def extract_team_from_question(question: str) -> Optional[str]:
    """Extract team name from question using aliases."""
    question_lower = question.lower()
    
    for team_name, aliases in TEAM_ALIASES.items():
        for alias in aliases:
            # Use word boundaries to avoid partial matches
            if re.search(rf'\b{re.escape(alias)}\b', question_lower):
                return team_name
    
    return None


def extract_player_from_question(question: str) -> Optional[str]:
    """Extract player name from question (basic implementation)."""
    # Look for patterns like "did [Name] score" or "[Name]'s stats"
    patterns = [
        r"(?:did|how many|what did)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\s+(?:score|get|have)",
        r"([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)'s\s+(?:stats|points|rebounds|assists)",
        r"(?:stats|points|rebounds)\s+(?:for|of)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)",
    ]
    
    for pattern in patterns:
        match = re.search(pattern, question)
        if match:
            return match.group(1)
    
    return None


# =============================================================================
# SEMANTIC PATTERNS - 30+ Comprehensive Coverage
# =============================================================================

SEMANTIC_PATTERNS = [
    # =========================================================================
    # CATEGORY: Individual Player Stats (1-15)
    # =========================================================================
    
    SemanticPattern(
        name="top_scorer_game",
        description="Find the top scorer in a game",
        category="individual",
        patterns=[
            r"(?:who|which player).*(?:top|leading|lead|most|highest).*scor",
            r"(?:top|leading|lead|highest).*scor",
            r"who scored (?:the )?most",
            r"leading scorer",
            r"lead scorer",
            r"most points",
            r"who (?:was|is) the (?:top|lead|best) scorer",
        ],
        sql_template="""
            SELECT player_name, points, team_name, rebounds, assists
            FROM players
            WHERE game_id = '{game_id}'
            ORDER BY points DESC
            LIMIT 1
        """,
        format_template="{player_name} led all scorers with {points} points ({team_name})"
    ),
    
    SemanticPattern(
        name="top_scorer_team",
        description="Find the top scorer for a specific team",
        category="individual",
        patterns=[
            r"(?:who|which player).*(?:top|leading|lead|most).*scor.*(?:for|on)\s+\w+",
            r"(?:\w+)(?:'s)?\s+(?:top|leading|lead|best)\s+scorer",
            r"who led (\w+) in (?:points|scoring)",
            r"lead scorer (?:for|on) (\w+)",
            r"(?:top|lead|best) scorer (?:for|on) (\w+)",
            r"who (?:was|is) the lead scorer for (\w+)",
        ],
        sql_template="""
            SELECT player_name, points, team_name, rebounds, assists
            FROM players
            WHERE game_id = '{game_id}'
              AND LOWER(team_name) LIKE '%{team}%'
            ORDER BY points DESC
            LIMIT 1
        """,
        format_template="{player_name} led {team_name} with {points} points"
    ),
    
    SemanticPattern(
        name="most_rebounds_game",
        description="Find player with most rebounds in game",
        category="individual",
        patterns=[
            r"(?:who|which player).*(?:most|leading|highest).*rebounds?",
            r"(?:most|leading).*rebounds?",
            r"rebound.*leader",
            r"who led.*rebounds",
        ],
        sql_template="""
            SELECT player_name, rebounds, team_name, offensive_rebounds, defensive_rebounds
            FROM players
            WHERE game_id = '{game_id}'
            ORDER BY rebounds DESC
            LIMIT 1
        """,
        format_template="{player_name} grabbed {rebounds} rebounds ({team_name})"
    ),
    
    SemanticPattern(
        name="most_rebounds_team",
        description="Find player with most rebounds for a team",
        category="individual",
        patterns=[
            r"who led (\w+) in rebounds",
            r"(\w+)(?:'s)? (?:top|leading) rebounder",
            r"most rebounds (?:for|on) (\w+)",
        ],
        sql_template="""
            SELECT player_name, rebounds, team_name, offensive_rebounds, defensive_rebounds
            FROM players
            WHERE game_id = '{game_id}'
              AND LOWER(team_name) LIKE '%{team}%'
            ORDER BY rebounds DESC
            LIMIT 1
        """,
        format_template="{player_name} led {team_name} with {rebounds} rebounds"
    ),
    
    SemanticPattern(
        name="most_assists_game",
        description="Find player with most assists in game",
        category="individual",
        patterns=[
            r"(?:who|which player).*(?:most|leading|highest).*assists?",
            r"(?:most|leading).*assists?",
            r"assist.*leader",
            r"who (?:led|had).*assists",
        ],
        sql_template="""
            SELECT player_name, assists, team_name, points
            FROM players
            WHERE game_id = '{game_id}'
            ORDER BY assists DESC
            LIMIT 1
        """,
        format_template="{player_name} dished out {assists} assists ({team_name})"
    ),
    
    SemanticPattern(
        name="most_assists_team",
        description="Find player with most assists for a team",
        category="individual",
        patterns=[
            r"who led (\w+) in assists",
            r"(\w+)(?:'s)? assist leader",
            r"most assists (?:for|on) (\w+)",
        ],
        sql_template="""
            SELECT player_name, assists, team_name, points
            FROM players
            WHERE game_id = '{game_id}'
              AND LOWER(team_name) LIKE '%{team}%'
            ORDER BY assists DESC
            LIMIT 1
        """,
        format_template="{player_name} led {team_name} with {assists} assists"
    ),
    
    SemanticPattern(
        name="most_steals",
        description="Find player with most steals",
        category="individual",
        patterns=[
            r"(?:who|which player).*(?:most|leading).*steals?",
            r"(?:most|leading).*steals?",
            r"steal.*leader",
        ],
        sql_template="""
            SELECT player_name, steals, team_name
            FROM players
            WHERE game_id = '{game_id}'
            ORDER BY steals DESC
            LIMIT 1
        """,
        format_template="{player_name} had {steals} steals ({team_name})"
    ),
    
    SemanticPattern(
        name="most_blocks",
        description="Find player with most blocks",
        category="individual",
        patterns=[
            r"(?:who|which player).*(?:most|leading).*blocks?",
            r"(?:most|leading).*blocks?",
            r"block.*leader",
            r"who blocked.*most",
        ],
        sql_template="""
            SELECT player_name, blocks, team_name
            FROM players
            WHERE game_id = '{game_id}'
            ORDER BY blocks DESC
            LIMIT 1
        """,
        format_template="{player_name} had {blocks} blocks ({team_name})"
    ),
    
    SemanticPattern(
        name="most_turnovers",
        description="Find player with most turnovers",
        category="individual",
        patterns=[
            r"(?:who|which player).*(?:most|leading).*turnovers?",
            r"(?:most|leading).*turnovers?",
            r"who turned.*over.*most",
        ],
        sql_template="""
            SELECT player_name, turnovers, team_name
            FROM players
            WHERE game_id = '{game_id}'
            ORDER BY turnovers DESC
            LIMIT 1
        """,
        format_template="{player_name} had {turnovers} turnovers ({team_name})"
    ),
    
    SemanticPattern(
        name="most_3pt_made",
        description="Find player with most 3-pointers made",
        category="individual",
        patterns=[
            r"(?:who|which player).*(?:most|leading).*(?:3|three).*(?:pointer|pt|point)",
            r"(?:most|leading).*(?:3|three).*(?:pointer|pt|made)",
            r"(?:3|three).*point.*leader",
            r"who made.*most.*(?:3|three)",
            r"most (?:3|three)s",
        ],
        sql_template="""
            SELECT player_name, fg3_made, fg3_attempted, team_name
            FROM players
            WHERE game_id = '{game_id}'
            ORDER BY fg3_made DESC
            LIMIT 1
        """,
        format_template="{player_name} made {fg3_made} three-pointers ({team_name})"
    ),
    
    SemanticPattern(
        name="most_3pt_team",
        description="Find player with most 3-pointers for a team",
        category="individual",
        patterns=[
            r"who (?:made|hit|shot).*most.*(?:3|three).*(?:for|on) (\w+)",
            r"(\w+)(?:'s)? (?:3|three).*point.*leader",
            r"most (?:3|three).*(?:for|on) (\w+)",
        ],
        sql_template="""
            SELECT player_name, fg3_made, fg3_attempted, team_name
            FROM players
            WHERE game_id = '{game_id}'
              AND LOWER(team_name) LIKE '%{team}%'
            ORDER BY fg3_made DESC
            LIMIT 1
        """,
        format_template="{player_name} led {team_name} with {fg3_made} three-pointers"
    ),
    
    SemanticPattern(
        name="best_fg_pct",
        description="Find player with best FG% (min 5 attempts)",
        category="individual",
        patterns=[
            r"(?:who|which player).*best.*(?:fg|field goal|shooting).*(?:pct|percent|%)",
            r"best.*shooter",
            r"highest.*(?:fg|field goal).*(?:pct|percent)",
            r"most efficient.*shooter",
        ],
        sql_template="""
            SELECT player_name, fg_made, fg_attempted, 
                   ROUND(CAST(fg_made AS FLOAT) / fg_attempted * 100, 1) as fg_pct,
                   team_name
            FROM players
            WHERE game_id = '{game_id}'
              AND fg_attempted >= 5
            ORDER BY fg_pct DESC
            LIMIT 1
        """,
        format_template="{player_name} shot {fg_pct}% ({fg_made}-{fg_attempted}) from the field ({team_name})"
    ),
    
    SemanticPattern(
        name="most_minutes",
        description="Find player with most minutes played",
        category="individual",
        patterns=[
            r"(?:who|which player).*(?:most|longest).*minutes",
            r"(?:most|longest).*minutes",
            r"who played.*(?:most|longest)",
            r"most playing time",
        ],
        sql_template="""
            SELECT player_name, minutes, team_name, points
            FROM players
            WHERE game_id = '{game_id}'
            ORDER BY minutes DESC
            LIMIT 1
        """,
        format_template="{player_name} played {minutes} minutes ({team_name})"
    ),
    
    SemanticPattern(
        name="double_double",
        description="Find players with double-doubles",
        category="individual",
        patterns=[
            r"(?:did anyone|who).*(?:get|have|record).*double.*double",
            r"double.*double",
            r"any double.*double",
        ],
        sql_template="""
            SELECT player_name, points, rebounds, assists, team_name
            FROM players
            WHERE game_id = '{game_id}'
              AND (
                (points >= 10 AND rebounds >= 10) OR
                (points >= 10 AND assists >= 10) OR
                (rebounds >= 10 AND assists >= 10)
              )
        """,
        format_template="{player_name} had a double-double with {points} points and {rebounds} rebounds ({team_name})"
    ),
    
    SemanticPattern(
        name="most_fouls",
        description="Find player with most fouls",
        category="individual",
        patterns=[
            r"(?:who|which player).*(?:most|leading).*fouls?",
            r"(?:most|leading).*fouls?",
            r"foul.*trouble",
        ],
        sql_template="""
            SELECT player_name, fouls, team_name, minutes
            FROM players
            WHERE game_id = '{game_id}'
            ORDER BY fouls DESC
            LIMIT 1
        """,
        format_template="{player_name} had {fouls} fouls ({team_name})"
    ),
    
    # =========================================================================
    # CATEGORY: Team Stats (16-25)
    # =========================================================================
    
    SemanticPattern(
        name="final_score",
        description="Get the final score of the game",
        category="team",
        patterns=[
            r"(?:what|final).*score",
            r"(?:score|result).*(?:game|match)",
            r"how (?:did|does).*(?:end|finish)",
            r"final.*(?:score|result)",
        ],
        sql_template="""
            SELECT away_team_name, away_team_score, home_team_name, home_team_score
            FROM games
            WHERE game_id = '{game_id}'
        """,
        format_template="{away_team_name} {away_team_score} - {home_team_name} {home_team_score}"
    ),
    
    SemanticPattern(
        name="winning_team",
        description="Find which team won",
        category="team",
        patterns=[
            r"who won",
            r"which team won",
            r"winner",
            r"(?:did|does) (\w+) win",
        ],
        sql_template="""
            SELECT 
                CASE WHEN home_team_score > away_team_score 
                     THEN home_team_name ELSE away_team_name END as winner,
                CASE WHEN home_team_score > away_team_score 
                     THEN home_team_score ELSE away_team_score END as winner_score,
                CASE WHEN home_team_score > away_team_score 
                     THEN away_team_name ELSE home_team_name END as loser,
                CASE WHEN home_team_score > away_team_score 
                     THEN away_team_score ELSE home_team_score END as loser_score
            FROM games
            WHERE game_id = '{game_id}'
        """,
        format_template="{winner} defeated {loser} {winner_score}-{loser_score}"
    ),
    
    SemanticPattern(
        name="point_margin",
        description="Find the margin of victory",
        category="team",
        patterns=[
            r"(?:margin|difference).*(?:victory|points|score)",
            r"(?:by how (?:many|much)|win by)",
            r"(?:how (?:close|big)).*(?:game|win|loss)",
            r"point.*(?:margin|difference|spread)",
        ],
        sql_template="""
            SELECT 
                ABS(home_team_score - away_team_score) as margin,
                CASE WHEN home_team_score > away_team_score 
                     THEN home_team_name ELSE away_team_name END as winner,
                CASE WHEN home_team_score > away_team_score 
                     THEN away_team_name ELSE home_team_name END as loser,
                home_team_score, away_team_score
            FROM games
            WHERE game_id = '{game_id}'
        """,
        format_template="{winner} won by {margin} points"
    ),
    
    SemanticPattern(
        name="team_total_points",
        description="Get total points for a specific team",
        category="team",
        patterns=[
            r"how many points (?:did|does) (\w+) (?:score|have)",
            r"(\w+)(?:'s)? (?:total )?points",
            r"(?:total|final) points (?:for|of) (\w+)",
        ],
        sql_template="""
            SELECT 
                CASE WHEN LOWER(home_team_name) LIKE '%{team}%' 
                     THEN home_team_name ELSE away_team_name END as team_name,
                CASE WHEN LOWER(home_team_name) LIKE '%{team}%' 
                     THEN home_team_score ELSE away_team_score END as points
            FROM games
            WHERE game_id = '{game_id}'
        """,
        format_template="{team_name} scored {points} points"
    ),
    
    SemanticPattern(
        name="team_rebounds",
        description="Get total rebounds for a team",
        category="team",
        patterns=[
            r"how many rebounds (?:did|does) (\w+) (?:have|get)",
            r"(\w+)(?:'s)? (?:total )?rebounds",
            r"team rebounds (?:for|of) (\w+)",
        ],
        sql_template="""
            SELECT team_name, SUM(rebounds) as total_rebounds,
                   SUM(offensive_rebounds) as offensive_reb,
                   SUM(defensive_rebounds) as defensive_reb
            FROM players
            WHERE game_id = '{game_id}'
              AND LOWER(team_name) LIKE '%{team}%'
            GROUP BY team_name
        """,
        format_template="{team_name} had {total_rebounds} total rebounds ({offensive_reb} offensive, {defensive_reb} defensive)"
    ),
    
    SemanticPattern(
        name="team_assists",
        description="Get total assists for a team",
        category="team",
        patterns=[
            r"how many assists (?:did|does) (\w+) (?:have|get)",
            r"(\w+)(?:'s)? (?:total )?assists",
            r"team assists (?:for|of) (\w+)",
        ],
        sql_template="""
            SELECT team_name, SUM(assists) as total_assists
            FROM players
            WHERE game_id = '{game_id}'
              AND LOWER(team_name) LIKE '%{team}%'
            GROUP BY team_name
        """,
        format_template="{team_name} had {total_assists} assists"
    ),
    
    SemanticPattern(
        name="team_fg_pct",
        description="Get field goal percentage for a team",
        category="team",
        patterns=[
            r"(?:what|how).*(\w+)(?:'s)?.*(?:field goal|fg|shooting).*(?:pct|percent|%)",
            r"(\w+).*shot.*(?:field|from the field)",
            r"team.*(?:fg|shooting).*(?:pct|percent)",
        ],
        sql_template="""
            SELECT team_name, 
                   SUM(fg_made) as fg_made, 
                   SUM(fg_attempted) as fg_attempted,
                   ROUND(CAST(SUM(fg_made) AS FLOAT) / SUM(fg_attempted) * 100, 1) as fg_pct
            FROM players
            WHERE game_id = '{game_id}'
              AND LOWER(team_name) LIKE '%{team}%'
            GROUP BY team_name
        """,
        format_template="{team_name} shot {fg_pct}% from the field ({fg_made}-{fg_attempted})"
    ),
    
    SemanticPattern(
        name="team_3pt_pct",
        description="Get 3-point percentage for a team",
        category="team",
        patterns=[
            r"(?:what|how).*(\w+)(?:'s)?.*(?:3|three).*(?:point|pt).*(?:pct|percent|%)",
            r"(\w+).*shot.*(?:3|three)",
            r"team.*(?:3|three).*(?:pct|percent)",
        ],
        sql_template="""
            SELECT team_name, 
                   SUM(fg3_made) as fg3_made, 
                   SUM(fg3_attempted) as fg3_attempted,
                   ROUND(CAST(SUM(fg3_made) AS FLOAT) / SUM(fg3_attempted) * 100, 1) as fg3_pct
            FROM players
            WHERE game_id = '{game_id}'
              AND LOWER(team_name) LIKE '%{team}%'
            GROUP BY team_name
        """,
        format_template="{team_name} shot {fg3_pct}% from three ({fg3_made}-{fg3_attempted})"
    ),
    
    SemanticPattern(
        name="team_turnovers",
        description="Get total turnovers for a team",
        category="team",
        patterns=[
            r"how many turnovers (?:did|does) (\w+) (?:have|commit)",
            r"(\w+)(?:'s)? (?:total )?turnovers",
            r"team turnovers (?:for|of) (\w+)",
        ],
        sql_template="""
            SELECT team_name, SUM(turnovers) as total_turnovers
            FROM players
            WHERE game_id = '{game_id}'
              AND LOWER(team_name) LIKE '%{team}%'
            GROUP BY team_name
        """,
        format_template="{team_name} committed {total_turnovers} turnovers"
    ),
    
    SemanticPattern(
        name="bench_points",
        description="Get bench scoring for a team",
        category="team",
        patterns=[
            r"bench (?:points|scoring)",
            r"(?:non-starters?|reserves?).*(?:points|score)",
            r"how many points.*bench",
        ],
        sql_template="""
            SELECT team_name, SUM(points) as bench_points
            FROM players
            WHERE game_id = '{game_id}'
              AND starter = 0
            GROUP BY team_name
            ORDER BY bench_points DESC
        """,
        format_template="{team_name} bench scored {bench_points} points"
    ),
    
    # =========================================================================
    # CATEGORY: Comparative (26-30)
    # =========================================================================
    
    SemanticPattern(
        name="better_shooting",
        description="Compare field goal percentages",
        category="comparative",
        patterns=[
            r"(?:which|who).*(?:team)?.*(?:shot|shoot).*better",
            r"(?:better|best).*(?:shooting|shooter)",
            r"(?:compare|comparison).*shooting",
            r"(?:who|which).*(?:more|higher).*(?:fg|field goal).*(?:pct|percent)",
        ],
        sql_template="""
            SELECT team_name, 
                   SUM(fg_made) as fg_made, 
                   SUM(fg_attempted) as fg_attempted,
                   ROUND(CAST(SUM(fg_made) AS FLOAT) / SUM(fg_attempted) * 100, 1) as fg_pct
            FROM players
            WHERE game_id = '{game_id}'
            GROUP BY team_name
            ORDER BY fg_pct DESC
        """,
        format_template="{team_name} shot better at {fg_pct}% ({fg_made}-{fg_attempted})"
    ),
    
    SemanticPattern(
        name="more_rebounds_compare",
        description="Compare rebounds between teams",
        category="comparative",
        patterns=[
            r"(?:which|who).*(?:team)?.*(?:more|most).*rebounds?",
            r"(?:out)?rebound",
            r"(?:compare|comparison).*rebounds?",
            r"(?:rebounding).*(?:edge|advantage)",
        ],
        sql_template="""
            SELECT team_name, SUM(rebounds) as total_rebounds
            FROM players
            WHERE game_id = '{game_id}'
            GROUP BY team_name
            ORDER BY total_rebounds DESC
        """,
        format_template="{team_name} won the rebounding battle with {total_rebounds} boards"
    ),
    
    SemanticPattern(
        name="more_turnovers_compare",
        description="Compare turnovers between teams",
        category="comparative",
        patterns=[
            r"(?:which|who).*(?:team)?.*(?:more|most|fewer|less).*turnovers?",
            r"turnover.*(?:battle|comparison|diff)",
            r"(?:better|worse).*(?:at )?(?:taking care|protecting)",
        ],
        sql_template="""
            SELECT team_name, SUM(turnovers) as total_turnovers
            FROM players
            WHERE game_id = '{game_id}'
            GROUP BY team_name
            ORDER BY total_turnovers ASC
        """,
        format_template="{team_name} was cleaner with the ball ({total_turnovers} turnovers)"
    ),
    
    SemanticPattern(
        name="close_game",
        description="Determine if game was close",
        category="comparative",
        patterns=[
            r"(?:was|is).*(?:this|the|it).*(?:close|tight).*game",
            r"(?:close|tight).*(?:game|contest)",
            r"(?:how close|margin)",
        ],
        sql_template="""
            SELECT 
                away_team_name, away_team_score, 
                home_team_name, home_team_score,
                ABS(home_team_score - away_team_score) as margin
            FROM games
            WHERE game_id = '{game_id}'
        """,
        format_template="The game was decided by {margin} points ({away_team_name} {away_team_score} - {home_team_name} {home_team_score})"
    ),
    
    SemanticPattern(
        name="starters_for_team",
        description="Get starters for a team",
        category="roster",
        patterns=[
            r"who started (?:for|on) (\w+)",
            r"(\w+)(?:'s)? (?:starting )?(?:lineup|five|starters)",
            r"starters (?:for|on) (\w+)",
        ],
        sql_template="""
            SELECT player_name, position, points, rebounds, assists
            FROM players
            WHERE game_id = '{game_id}'
              AND LOWER(team_name) LIKE '%{team}%'
              AND starter = 1
            ORDER BY points DESC
        """,
        format_template="{player_name} ({position}) started with {points} pts, {rebounds} reb, {assists} ast"
    ),
]


# =============================================================================
# SEMANTIC LAYER CLASS
# =============================================================================

class EnhancedSemanticLayer:
    """
    Enhanced semantic layer with 30+ patterns for fair comparison.
    """
    
    def __init__(self, db_path: Path, patterns: list[SemanticPattern] = None):
        self.db_path = db_path
        self.patterns = patterns or SEMANTIC_PATTERNS
    
    def match_pattern(self, question: str) -> tuple[SemanticPattern, dict, float] | None:
        """
        Find best matching pattern for a question.
        
        Returns:
            Tuple of (pattern, extracted_params, confidence) or None
        """
        question_lower = question.lower().strip()
        
        best_match = None
        best_score = 0.0
        best_params = {}
        
        for pattern in self.patterns:
            for regex in pattern.patterns:
                match = re.search(regex, question_lower, re.IGNORECASE)
                if match:
                    # Calculate confidence based on match quality
                    coverage = len(match.group()) / len(question_lower)
                    score = min(0.95, 0.7 + (coverage * 0.25))
                    
                    if score > best_score:
                        best_score = score
                        best_match = pattern
                        
                        # Extract parameters
                        params = {}
                        
                        # Try to extract team from question
                        team = extract_team_from_question(question)
                        if team:
                            params["team"] = team
                        
                        # Try to extract player from question
                        player = extract_player_from_question(question)
                        if player:
                            params["player"] = player
                        
                        best_params = params
        
        if best_match:
            return (best_match, best_params, best_score)
        
        return None
    
    def ask(self, question: str, game_id: str) -> dict | None:
        """
        Answer a question using the semantic layer.
        
        Args:
            question: User's question
            game_id: The game to query about
            
        Returns:
            Dict with answer, sql_query, confidence, pattern_name or None
        """
        match_result = self.match_pattern(question)
        
        if not match_result:
            return None
        
        pattern, params, confidence = match_result
        
        # Build SQL query
        sql = pattern.sql_template.format(game_id=game_id, **params)
        
        # Execute query
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(sql)
            rows = cursor.fetchall()
            conn.close()
            
            if not rows:
                return {
                    "answer": "No data found matching your question",
                    "sql_query": sql.strip(),
                    "confidence": 0.3,
                    "pattern_name": pattern.name,
                }
            
            # Format first result (or all for list queries)
            if len(rows) == 1:
                row_dict = dict(rows[0])
                answer = pattern.format_result(row_dict)
            else:
                # Multiple results - format each
                answers = [pattern.format_result(dict(row)) for row in rows[:5]]
                answer = "; ".join(answers)
                if len(rows) > 5:
                    answer += f" (and {len(rows) - 5} more)"
            
            return {
                "answer": answer,
                "sql_query": sql.strip(),
                "confidence": confidence,
                "pattern_name": pattern.name,
            }
            
        except Exception as e:
            return {
                "answer": f"Query error: {str(e)}",
                "sql_query": sql.strip(),
                "confidence": 0.0,
                "pattern_name": pattern.name,
            }


# =============================================================================
# CONVENIENCE FUNCTION
# =============================================================================

def create_semantic_layer(db_path: Path | None = None) -> EnhancedSemanticLayer:
    """Create an enhanced semantic layer instance."""
    if db_path is None:
        db_path = Path(__file__).parent.parent / "ncaa_basketball.db"
    return EnhancedSemanticLayer(db_path=db_path)
