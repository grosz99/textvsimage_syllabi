"""
Visual Context vs SQL: NCAA Basketball Analytics Demo

A Streamlit application that demonstrates how visual context analysis
can be as powerful as traditional text-to-SQL for answering analytical questions.

Run with: streamlit run app.py
"""

import os
import time
import sqlite3
import concurrent.futures
from pathlib import Path
from dataclasses import dataclass
from typing import Optional

import streamlit as st
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# =============================================================================
# CONFIGURATION
# =============================================================================

BASE_DIR = Path(__file__).parent
DB_PATH = BASE_DIR / "ncaa_basketball.db"
SCREENSHOTS_DIR = BASE_DIR / "screenshots"

QUICK_QUESTIONS = [
    "Who was the top scorer?",
    "What was the final score?",
    "Who had the most rebounds?",
    "Who made the most 3-pointers?",
]

# Team colors for visual indicators
TEAM_COLORS = {
    "DUKE": "#003087", "UNC": "#7BAFD4", "WAKE": "#9E7E38", "UVA": "#232D4B",
    "ARIZ": "#CC0033", "TCU": "#4D1979", "TEX": "#BF5700", "ALA": "#9E1B32",
    "AUB": "#0C2340", "ARK": "#9D2235", "BYU": "#002E5D", "UTAH": "#CC0000",
    "TTU": "#CC0000", "COLO": "#CFB87C", "ISU": "#C8102E", "OKST": "#FF7300",
    "SMU": "#C8102E", "STAN": "#8C1515", "UGA": "#BA0C2F", "SC": "#73000A",
}


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class GameInfo:
    """Information about a game with screenshot."""
    game_id: str
    away_team: str
    away_abbrev: str
    away_score: int
    home_team: str
    home_abbrev: str
    home_score: int
    status: str
    screenshot_path: Optional[Path]
    game_date: str


@dataclass
class AgentResult:
    """Result from an agent."""
    answer: Optional[str]
    confidence: float
    time_ms: int
    error: Optional[str] = None
    sql_query: Optional[str] = None
    pattern_name: Optional[str] = None
    screenshot_path: Optional[str] = None


# =============================================================================
# DATABASE FUNCTIONS
# =============================================================================

def get_games_with_screenshots() -> list[GameInfo]:
    """Get all games that have both database records and screenshots."""
    if not DB_PATH.exists():
        return []

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT DISTINCT
            g.game_id,
            g.away_team_name,
            g.away_team_abbrev,
            g.away_team_score,
            g.home_team_name,
            g.home_team_abbrev,
            g.home_team_score,
            g.status,
            g.game_date,
            s.file_path
        FROM games g
        INNER JOIN screenshots s ON g.game_id = s.game_id
        WHERE g.status LIKE '%FINAL%'
        ORDER BY g.game_date DESC
    """)

    rows = cursor.fetchall()
    conn.close()

    games = []
    for row in rows:
        screenshot_path = Path(row[9]) if row[9] else None

        if screenshot_path and not screenshot_path.is_absolute():
            screenshot_path = BASE_DIR / screenshot_path

        if screenshot_path and screenshot_path.exists():
            games.append(GameInfo(
                game_id=row[0],
                away_team=row[1] or "Away",
                away_abbrev=row[2] or "AWY",
                away_score=row[3] or 0,
                home_team=row[4] or "Home",
                home_abbrev=row[5] or "HME",
                home_score=row[6] or 0,
                status=row[7] or "Final",
                game_date=row[8] or "",
                screenshot_path=screenshot_path
            ))

    return games


# =============================================================================
# AGENT FUNCTIONS
# =============================================================================

def run_visual_agent(question: str, game_id: str, screenshot_path: Path, api_key: str) -> AgentResult:
    """Run the vision agent."""
    start = time.time()

    try:
        from src.services.anthropic import AnthropicService
        from src.agents.vision_agent import VisionAgent

        anthropic = AnthropicService(api_key=api_key)
        agent = VisionAgent(
            anthropic_service=anthropic,
            db_path=DB_PATH,
            screenshots_dir=SCREENSHOTS_DIR,
        )

        result = agent.ask(question, game_id=game_id, screenshot_path=screenshot_path)
        elapsed = int((time.time() - start) * 1000)

        return AgentResult(
            answer=result.answer,
            confidence=result.confidence,
            time_ms=elapsed,
            screenshot_path=str(screenshot_path) if result.answer else None,
            error=result.error
        )

    except Exception as e:
        return AgentResult(
            answer=None,
            confidence=0.0,
            time_ms=int((time.time() - start) * 1000),
            error=f"Vision analysis failed: {str(e)}"
        )


def run_sql_agent(question: str, game_id: str, api_key: str) -> AgentResult:
    """Run the analyst agent using Claude to generate SQL."""
    start = time.time()

    try:
        from src.services.anthropic import AnthropicService
        from src.agents.analyst_agent import AnalystAgent

        anthropic = AnthropicService(api_key=api_key)
        agent = AnalystAgent(
            anthropic_service=anthropic,
            db_path=DB_PATH,
        )

        result = agent.ask(question, game_id)
        elapsed = int((time.time() - start) * 1000)

        return AgentResult(
            answer=result.answer,
            confidence=result.confidence,
            time_ms=elapsed,
            sql_query=result.sql_query,
            error=result.error
        )

    except Exception as e:
        return AgentResult(
            answer=None,
            confidence=0.0,
            time_ms=int((time.time() - start) * 1000),
            error=f"Analyst agent failed: {str(e)}"
        )


# =============================================================================
# MAIN APPLICATION
# =============================================================================

def main():
    st.set_page_config(
        page_title="Visual Context vs SQL",
        page_icon="",
        layout="wide",
        initial_sidebar_state="collapsed"
    )

    # Custom CSS for clean design matching reference
    st.markdown("""
    <style>
        /* Hide default streamlit elements */
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}

        /* Main container */
        .main .block-container {
            padding-top: 2rem;
            padding-bottom: 2rem;
            max-width: 1200px;
        }

        /* Game card styling */
        .game-card {
            background: white;
            border: 1px solid #e0e0e0;
            border-radius: 12px;
            padding: 16px;
            margin: 8px 4px;
            cursor: pointer;
            transition: all 0.2s ease;
            min-height: 120px;
        }
        .game-card:hover {
            border-color: #6366f1;
            box-shadow: 0 4px 12px rgba(99, 102, 241, 0.15);
        }
        .game-card.selected {
            border: 2px solid #6366f1;
            background: #f8f7ff;
        }
        .team-row {
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin: 6px 0;
        }
        .team-name {
            display: flex;
            align-items: center;
            gap: 8px;
            font-weight: 500;
            color: #374151;
        }
        .team-dot {
            width: 10px;
            height: 10px;
            border-radius: 50%;
        }
        .team-score {
            font-weight: 700;
            font-size: 1.1em;
            color: #111827;
        }
        .game-status {
            font-size: 0.75em;
            color: #9ca3af;
            margin-top: 8px;
        }

        /* Question section */
        .question-header {
            font-size: 2rem;
            font-weight: 300;
            color: #374151;
            text-align: center;
            margin: 2rem 0 0.5rem 0;
        }
        .question-subtext {
            text-align: center;
            color: #9ca3af;
            margin-bottom: 1.5rem;
        }

        /* Quick question chips */
        .chip {
            display: inline-block;
            padding: 8px 16px;
            background: #f3f4f6;
            border-radius: 20px;
            margin: 4px;
            font-size: 0.85em;
            color: #6b7280;
            cursor: pointer;
            transition: all 0.2s;
        }
        .chip:hover {
            background: #e5e7eb;
            color: #374151;
        }

        /* Result panels */
        .result-panel {
            background: white;
            border: 1px solid #e0e0e0;
            border-radius: 12px;
            padding: 20px;
            height: 100%;
        }
        .panel-header {
            display: flex;
            align-items: center;
            gap: 8px;
            margin-bottom: 4px;
        }
        .panel-title {
            font-weight: 600;
            color: #111827;
        }
        .panel-subtitle {
            font-size: 0.8em;
            color: #9ca3af;
            margin-bottom: 16px;
        }
        .panel-dot {
            width: 8px;
            height: 8px;
            border-radius: 50%;
        }

        /* Metrics */
        .metric-row {
            display: flex;
            gap: 24px;
            margin-top: 16px;
        }
        .metric-item {
            text-align: center;
        }
        .metric-value {
            font-size: 1.5em;
            font-weight: 600;
            color: #111827;
        }
        .metric-label {
            font-size: 0.75em;
            color: #9ca3af;
            text-transform: uppercase;
        }

        /* Input styling */
        .stTextInput > div > div > input {
            border-radius: 25px;
            border: 1px solid #e0e0e0;
            padding: 12px 20px;
        }

        /* Button styling */
        .stButton > button {
            border-radius: 25px;
            padding: 8px 20px;
            font-weight: 500;
        }

        /* Section header */
        .section-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 16px;
        }
        .section-title {
            font-size: 0.85em;
            font-weight: 600;
            color: #6b7280;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }
        .view-all {
            font-size: 0.85em;
            color: #6366f1;
            cursor: pointer;
        }
    </style>
    """, unsafe_allow_html=True)

    # Sidebar for API key input
    with st.sidebar:
        st.header("Settings")

        # Check for API key in secrets first, then env, then manual input
        api_key = None

        # Try Streamlit secrets first
        try:
            if "ANTHROPIC_API_KEY" in st.secrets:
                api_key = st.secrets["ANTHROPIC_API_KEY"]
                if api_key and api_key != "your-key-here":
                    st.success("API Key loaded from secrets")
                else:
                    api_key = None
        except Exception:
            pass

        # If no secrets, try environment variable
        if not api_key:
            api_key = os.environ.get("ANTHROPIC_API_KEY", "")
            if api_key:
                st.success("API Key loaded from environment")

        # If still no key, show manual input
        if not api_key:
            api_key = st.text_input(
                "Anthropic API Key",
                type="password",
                placeholder="sk-ant-...",
                help="Enter your Anthropic API key to use the agents"
            )

            if api_key:
                st.success("API Key entered")
            else:
                st.warning("Please enter your API key to ask questions")

        st.divider()

        # About section
        st.markdown("""
        ### About This Demo

        Compare two approaches to answering
        analytics questions:

        **Vision Agent**
        Analyzes dashboard screenshots using
        Claude's vision capabilities

        **Analyst Agent**
        Generates SQL queries dynamically
        using Claude

        Both agents use the same underlying
        Claude model but different data sources.
        """)

    # Initialize session state
    if "selected_game_id" not in st.session_state:
        st.session_state.selected_game_id = None
    if "visual_result" not in st.session_state:
        st.session_state.visual_result = None
    if "sql_result" not in st.session_state:
        st.session_state.sql_result = None
    if "current_question" not in st.session_state:
        st.session_state.current_question = None

    # Load games
    games = get_games_with_screenshots()

    # ==========================================================================
    # TODAY'S GAMES SECTION
    # ==========================================================================
    st.markdown("""
    <div class="section-header">
        <span class="section-title">Select a Game to Analyze</span>
        <span class="view-all">View All</span>
    </div>
    """, unsafe_allow_html=True)

    if not games:
        st.warning("No games with screenshots found. Please check database connection.")
    else:
        # Show selection prompt if no game selected
        if not st.session_state.selected_game_id:
            st.info("Click on a game below to select it, then ask questions about that game.")

        # Display game cards in columns - show more games
        num_cols = min(len(games), 5)
        cols = st.columns(num_cols)

        for idx, game in enumerate(games[:10]):
            col_idx = idx % num_cols
            with cols[col_idx]:
                is_selected = game.game_id == st.session_state.selected_game_id
                away_color = TEAM_COLORS.get(game.away_abbrev, "#6366f1")
                home_color = TEAM_COLORS.get(game.home_abbrev, "#6366f1")

                card_class = "game-card selected" if is_selected else "game-card"

                st.markdown(f"""
                <div class="{card_class}">
                    <div class="team-row">
                        <div class="team-name">
                            <div class="team-dot" style="background: {away_color};"></div>
                            {game.away_abbrev}
                        </div>
                        <div class="team-score">{game.away_score}</div>
                    </div>
                    <div class="team-row">
                        <div class="team-name">
                            <div class="team-dot" style="background: {home_color};"></div>
                            {game.home_abbrev}
                        </div>
                        <div class="team-score">{game.home_score}</div>
                    </div>
                    <div class="game-status">FINAL</div>
                </div>
                """, unsafe_allow_html=True)

                if st.button("Select" if not is_selected else "Selected",
                           key=f"game_{game.game_id}",
                           use_container_width=True,
                           type="primary" if is_selected else "secondary"):
                    st.session_state.selected_game_id = game.game_id
                    st.session_state.visual_result = None
                    st.session_state.sql_result = None
                    st.rerun()

    # ==========================================================================
    # QUESTION SECTION
    # ==========================================================================
    st.markdown("""
    <div class="question-header">What would you like to know?</div>
    <div class="question-subtext">Ask about player matchups, team efficiencies, or historical comparisons.</div>
    """, unsafe_allow_html=True)

    # Get selected game
    selected_game = None
    if st.session_state.selected_game_id:
        for game in games:
            if game.game_id == st.session_state.selected_game_id:
                selected_game = game
                break

    # Context indicator ABOVE the input
    if selected_game:
        st.markdown(f"**Context:** {selected_game.away_team} vs {selected_game.home_team}")
    else:
        st.warning("Please select a game above first")

    # Question input row
    col1, col2 = st.columns([5, 1])

    with col1:
        # Dynamic placeholder based on selected game
        if selected_game:
            placeholder = f"e.g., Who was the lead scorer for {selected_game.home_abbrev}?"
        else:
            placeholder = "Select a game first..."

        question = st.text_input(
            "Question",
            placeholder=placeholder,
            label_visibility="collapsed",
            key="question_input",
            disabled=not selected_game
        )

    with col2:
        submit_clicked = st.button("Ask", type="primary", use_container_width=True, disabled=not selected_game)

    # Quick question chips - NOW BELOW the input bar
    if selected_game:
        st.caption("Quick questions:")
        chip_cols = st.columns(len(QUICK_QUESTIONS))

        quick_question_clicked = None
        for idx, q in enumerate(QUICK_QUESTIONS):
            with chip_cols[idx]:
                if st.button(q, key=f"quick_{idx}", use_container_width=True):
                    quick_question_clicked = q
    else:
        quick_question_clicked = None

    st.markdown("---")

    # Anchor for auto-scroll to results
    results_anchor = st.empty()

    # ==========================================================================
    # PROCESS QUESTION
    # ==========================================================================
    question_to_process = None
    if submit_clicked and question:
        question_to_process = question
    elif quick_question_clicked:
        question_to_process = quick_question_clicked

    if question_to_process and selected_game:
        if not api_key:
            st.error("Please set ANTHROPIC_API_KEY in your .env file")
        else:
            st.session_state.current_question = question_to_process

            # Show processing status in a visible area
            status_container = st.container()
            with status_container:
                st.info(f"Analyzing: **{question_to_process}**")
                progress_bar = st.progress(0, text="Starting agents...")

            with st.spinner("Running both agents..."):
                with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
                    visual_future = executor.submit(
                        run_visual_agent,
                        question_to_process,
                        selected_game.game_id,
                        selected_game.screenshot_path,
                        api_key
                    )
                    sql_future = executor.submit(
                        run_sql_agent,
                        question_to_process,
                        selected_game.game_id,
                        api_key
                    )

                    progress_bar.progress(50, text="Vision Agent analyzing image...")
                    st.session_state.visual_result = visual_future.result()
                    progress_bar.progress(75, text="Analyst Agent generating SQL...")
                    st.session_state.sql_result = sql_future.result()
                    progress_bar.progress(100, text="Complete!")

    # ==========================================================================
    # RESULTS SECTION
    # ==========================================================================
    if st.session_state.visual_result or st.session_state.sql_result:
        # Auto-scroll anchor - this div will be scrolled into view
        st.markdown('<div id="results-section"></div>', unsafe_allow_html=True)

        # Results header with the question asked
        if st.session_state.current_question:
            st.markdown(f"### Results for: *{st.session_state.current_question}*")

        # JavaScript to scroll to results section
        st.markdown("""
            <script>
                const resultsSection = document.getElementById('results-section');
                if (resultsSection) {
                    resultsSection.scrollIntoView({behavior: 'smooth', block: 'start'});
                }
            </script>
        """, unsafe_allow_html=True)

        st.markdown("---")

        col1, col2 = st.columns(2)

        # Vision Agent Panel
        with col1:
            st.markdown("""
            <div class="result-panel">
                <div class="panel-header">
                    <div class="panel-dot" style="background: #8b5cf6;"></div>
                    <span class="panel-title">Vision Agent</span>
                </div>
                <div class="panel-subtitle">VISUAL ANALYSIS</div>
            </div>
            """, unsafe_allow_html=True)

            result = st.session_state.visual_result
            if result:
                # Show screenshot first for verification
                if result.screenshot_path:
                    screenshot = Path(result.screenshot_path)
                    if screenshot.exists():
                        st.image(str(screenshot), use_container_width=True)

                if result.error:
                    st.error(result.error)
                elif result.answer:
                    st.markdown(f"**{result.answer}**")

                    # Metrics
                    m1, m2 = st.columns(2)
                    with m1:
                        st.metric("Confidence", f"{int(result.confidence * 100)}%")
                    with m2:
                        st.metric("Response Time", f"{result.time_ms}ms")

        # Analyst Agent Panel
        with col2:
            st.markdown("""
            <div class="result-panel">
                <div class="panel-header">
                    <div class="panel-dot" style="background: #f97316;"></div>
                    <span class="panel-title">Analyst Agent</span>
                </div>
                <div class="panel-subtitle">DATABASE QUERY</div>
            </div>
            """, unsafe_allow_html=True)

            result = st.session_state.sql_result
            if result:
                if result.error:
                    st.error(result.error)
                elif result.answer:
                    st.markdown(f"**{result.answer}**")

                    # Metrics
                    m1, m2 = st.columns(2)
                    with m1:
                        st.metric("Confidence", f"{int(result.confidence * 100)}%")
                    with m2:
                        st.metric("Response Time", f"{result.time_ms}ms")

                # Always show SQL Query (expanded)
                if result.sql_query:
                    st.caption("Generated SQL:")
                    st.code(result.sql_query, language="sql")


if __name__ == "__main__":
    main()
