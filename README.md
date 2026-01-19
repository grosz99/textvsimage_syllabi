# Visual Context vs SQL Demo

A Streamlit application demonstrating how AI image analysis compares to traditional SQL database queries for answering analytics questions.

## Overview

This demo compares two approaches to answering questions about NCAA basketball game data:

- **Vision Agent**: Analyzes dashboard screenshots using Claude's vision capabilities
- **Analyst Agent**: Generates SQL queries dynamically using Claude

Both agents use the same underlying Claude model but different data sources - proving that dashboard images can be just as verifiable as structured SQL queries.

## Setup

1. Clone the repository:
```bash
git clone https://github.com/grosz99/textvsimage_syllabi.git
cd textvsimage_syllabi
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Run the application:
```bash
streamlit run app.py
```

4. Enter your Anthropic API key in the sidebar when prompted.

## Features

- Select from 10 NCAA basketball games with boxscore screenshots
- Ask natural language questions about player stats, scores, and comparisons
- Compare answers from both Vision Agent and Analyst Agent side-by-side
- View the generated SQL queries from the Analyst Agent
- See the actual screenshot analyzed by the Vision Agent

## Project Structure

```
textvsimage_syllabi/
├── app.py                    # Main Streamlit application
├── src/
│   ├── agents/
│   │   ├── vision_agent.py   # Claude Vision analysis
│   │   └── analyst_agent.py  # Claude SQL generation
│   └── services/
│       └── anthropic.py      # Anthropic API wrapper
├── config/
│   └── semantic_patterns.py  # SQL pattern templates
├── screenshots/              # Game boxscore images
├── ncaa_basketball.db        # SQLite database
└── requirements.txt
```

## Requirements

- Python 3.10+
- Anthropic API key
- See `requirements.txt` for Python dependencies

## License

MIT
