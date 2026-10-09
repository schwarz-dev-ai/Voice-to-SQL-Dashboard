# Product Requirement Document (PRD) - Voice-to-SQL Dashboard

## 1. Project Overview
The **Voice-to-SQL Dashboard** is an intelligent web application that allows non-technical users to query a database using natural language. The app translates the user's natural language input into a valid SQL query via the Claude API, executes it against a local SQLite database, and presents the results in a clean, visual dashboard.

## 2. Core Features
- **Database Backend:** A pre-seeded SQLite database containing mock e-commerce data (Customers, Orders, Products).
- **Natural Language Input:** A text input field (with structural readiness for voice-to-text transcripts) where users can ask questions like "Who are the top 5 customers by total spending?".
- **Claude API Integration:** A backend service that sends the schema and user prompt to Claude, receiving a raw, executable SQL query in return.
- **Data Execution & Presentation:** The system executes the SQL query safely and displays the result in a dynamic HTML table or basic chart.
- **Safety / Query Validation:** Simple validation to ensure only `SELECT` queries are executed (preventing `DROP` or `DELETE`).

## 3. Tech Stack
- **Frontend:** Streamlit (Python) or HTML/JS with Tailwind CSS for rapid prototyping and clean UI.
- **Backend:** Python (FastAPI or Flask) to handle API requests and SQLite interaction.
- **LLM:** Anthropic Claude API (using the provided workshop API key).
- **Database:** SQLite (file-based, lightweight, zero setup).

## 4. MVP Timeline (Target: 14:45)
- **Phase 1 (12:00 - 12:45):** Setup SQLite mock database and basic Python backend.
- **Phase 2 (12:45 - 13:45):** Integrate Claude API for Text-to-SQL translation with strict system prompting.
- **Phase 3 (13:45 - 14:30):** Build the Streamlit/Web Frontend and connect it to the backend.
- **Phase 4 (14:30 - 14:45):** Testing, refinement, and preparation for the presentation.
