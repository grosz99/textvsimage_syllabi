"""
Analyst Agent for SQL Query Generation

Uses Claude to generate SQL queries based on natural language questions,
guided by the database schema and semantic patterns.
"""

import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from src.services.anthropic import AnthropicService


@dataclass
class AnalystResult:
    """Result from the Analyst Agent."""
    answer: Optional[str]
    confidence: float
    sql_query: Optional[str] = None
    error: Optional[str] = None


class AnalystAgent:
    """Agent that generates and executes SQL queries using Claude."""

    def __init__(
        self,
        anthropic_service: AnthropicService,
        db_path: Path,
    ):
        self.anthropic = anthropic_service
        self.db_path = db_path
        self.schema = self._get_schema()

    def _get_schema(self) -> str:
        """Get the database schema for context."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Get table info
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()

        schema_parts = []
        for (table_name,) in tables:
            if table_name.startswith('sqlite'):
                continue
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = cursor.fetchall()
            col_defs = [f"  {col[1]} {col[2]}" for col in columns]
            schema_parts.append(f"{table_name}:\n" + "\n".join(col_defs))

        conn.close()
        return "\n\n".join(schema_parts)

    def _get_sample_data(self, game_id: str) -> str:
        """Get sample data for context."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Get game info
        cursor.execute("""
            SELECT away_team_name, away_team_abbrev, away_team_score,
                   home_team_name, home_team_abbrev, home_team_score
            FROM games WHERE game_id = ?
        """, (game_id,))
        game = cursor.fetchone()

        # Get team names in the game
        cursor.execute("""
            SELECT DISTINCT team_name FROM players WHERE game_id = ?
        """, (game_id,))
        teams = [r[0] for r in cursor.fetchall()]

        # Get sample players
        cursor.execute("""
            SELECT player_name, team_name, points, rebounds, assists
            FROM players WHERE game_id = ? LIMIT 5
        """, (game_id,))
        players = cursor.fetchall()

        conn.close()

        sample = f"""Game: {game[0]} ({game[1]}) {game[2]} vs {game[3]} ({game[4]}) {game[5]}
Teams in data: {', '.join(teams)}
Sample players: {players[:3]}"""

        return sample

    def ask(self, question: str, game_id: str) -> AnalystResult:
        """
        Answer a question by generating and executing SQL.

        Args:
            question: Natural language question
            game_id: Game ID to query

        Returns:
            AnalystResult with answer and SQL query
        """
        sample_data = self._get_sample_data(game_id)

        # Build prompt for Claude to generate SQL
        prompt = f"""You are a SQL expert analyzing NCAA basketball game data.

DATABASE SCHEMA:
{self.schema}

CURRENT GAME CONTEXT:
{sample_data}
Game ID: {game_id}

USER QUESTION: {question}

Generate a SQL query to answer this question. Important rules:
1. Always filter by game_id = '{game_id}'
2. Team names may be partial matches - use LIKE '%team%' for flexibility
3. For "2nd most" or ordinal queries, use LIMIT with OFFSET or ROW_NUMBER
4. Common abbreviations: ALA=Alabama, TEX=Texas, DUKE=Duke, UNC=North Carolina, etc.

Respond in this exact format:
SQL: <your sql query here>
EXPLANATION: <brief explanation of what the query does>"""

        try:
            # Call Claude to generate SQL
            response = self.anthropic.client.messages.create(
                model=self.anthropic.model,
                max_tokens=1024,
                messages=[{"role": "user", "content": prompt}]
            )

            response_text = response.content[0].text

            # Parse SQL from response
            sql_query = self._extract_sql(response_text)

            if not sql_query:
                return AnalystResult(
                    answer=None,
                    confidence=0.0,
                    error="Could not generate SQL query"
                )

            # Execute the query
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            try:
                cursor.execute(sql_query)
                results = cursor.fetchall()
                columns = [desc[0] for desc in cursor.description] if cursor.description else []
            except Exception as e:
                conn.close()
                return AnalystResult(
                    answer=None,
                    confidence=0.0,
                    sql_query=sql_query,
                    error=f"SQL execution error: {str(e)}"
                )

            conn.close()

            if not results:
                return AnalystResult(
                    answer="No data found for this query",
                    confidence=0.5,
                    sql_query=sql_query
                )

            # Format the answer
            answer = self._format_answer(question, results, columns)

            return AnalystResult(
                answer=answer,
                confidence=0.9,
                sql_query=sql_query
            )

        except Exception as e:
            return AnalystResult(
                answer=None,
                confidence=0.0,
                error=f"Analyst agent error: {str(e)}"
            )

    def _extract_sql(self, response: str) -> Optional[str]:
        """Extract SQL query from Claude's response."""
        lines = response.split('\n')
        sql_lines = []
        in_sql = False

        for line in lines:
            if line.strip().upper().startswith('SQL:'):
                in_sql = True
                # Get content after "SQL:"
                sql_content = line.split(':', 1)[1].strip()
                if sql_content:
                    sql_lines.append(sql_content)
            elif in_sql:
                if line.strip().upper().startswith('EXPLANATION:'):
                    break
                sql_lines.append(line)

        sql = ' '.join(sql_lines).strip()

        # Clean up common issues
        sql = sql.replace('```sql', '').replace('```', '').strip()

        return sql if sql else None

    def _format_answer(self, question: str, results: list, columns: list) -> str:
        """Format query results into a natural language answer."""
        if not results:
            return "No results found"

        # For single row results
        if len(results) == 1:
            row = results[0]
            if len(columns) >= 2:
                # Assume first column is name, rest are stats
                parts = []
                for i, col in enumerate(columns):
                    if i == 0:
                        parts.append(str(row[i]))
                    else:
                        parts.append(f"{row[i]} {col}")
                return " - ".join(parts)

        # For multiple rows, list them
        answers = []
        for row in results[:5]:  # Limit to 5
            if columns:
                answers.append(f"{row[0]}: {row[1] if len(row) > 1 else ''}")
            else:
                answers.append(str(row))

        return "; ".join(answers)
