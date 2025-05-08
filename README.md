# Inventory AI Agent

## Project Goal

The Inventory AI Agent aims to be an intelligent assistant that empowers non-technical staff to **interact with, analyze, and manage** an inventory database using natural language commands through a simple chat interface. The goal is to bridge the gap between conversational requests and structured database operations, making inventory data more accessible and actionable without requiring knowledge of SQL or complex reporting tools.

## Features

This project provides a backend API and frontend interface designed to deliver the following capabilities:

1.  **Natural Language Interaction:**
    * Accept user commands and questions about inventory written in plain English (e.g., "How many widgets do we have?", "Show items low on stock", "Record sale of 5 units of X", "Add 20 units of Y").
    * Leverage OpenAI's GPT models to accurately understand the user's intent, including follow-up questions within a conversation.

2.  **AI-Powered Database Operations:**
    * Translate the user's intent into parameterized SQLite queries (`SELECT`, `UPDATE`).
    * Focus operations on the inventory database and relevant data fields.

3.  **Data Querying & Analysis:**
    * Retrieve specific data points or lists based on user criteria.
    * Provide AI-generated natural language explanations summarizing query results.

4.  **Inventory Management:**
    * Allow users to update inventory levels through commands like recording sales or adding stock, modifying the appropriate data fields.
    * Include necessary business logic checks (e.g., preventing sales if stock is insufficient, verifying item existence).

5.  **Data Visualization:**
    * Generate relevant charts (bar, pie, line, scatter) based on user requests or query results.
    * Return visualizations directly within the chat interface.

6.  **Security & Safety:**
    * Include a validation layer using `sqlparse` to ensure generated SQL (`SELECT`, `UPDATE`) only interacts with allowed database structures and follows safe patterns.
    * Implement basic permissions to control who can perform data modification actions.

7.  **Conversational Context:**
    * Maintain session history to understand context and follow-up questions naturally.

8.  **User Interface:**
    * Provide a simple, web-based chat interface for user interaction.

9.  **Error Handling:**
    * Provide informative feedback if a query cannot be understood, fails validation, or encounters a database/logic issue.

## Technology Stack

* **Backend:**
    * Language: Python 3
    * Web Framework: FastAPI
    * Database: SQLite
    * AI Model: OpenAI API (GPT-4o or compatible)
    * Charting: Matplotlib
    * SQL Parsing: sqlparse
    * Dependencies: See `requirements.txt`
* **Frontend (MVP):** HTML, CSS, JavaScript

## Running the Application

### Option 1: Using the Launcher Scripts (Recommended)

#### For Mac/Linux Users:
1. Open a terminal in the project root directory
2. Run the launcher script:
   ```bash
   ./start_app.sh
   ```
3. Both the backend and frontend will start automatically
4. The frontend will open in your default browser
5. Press Ctrl+C in the terminal when you want to stop both servers

#### For Windows Users:
1. Open the project in File Explorer
2. Double-click `start_app.bat`
3. Two command windows will open (one for backend, one for frontend)
4. The frontend will open in your default browser
5. Close both command windows when you're done

### Option 2: Manual Startup

If you prefer to start the services manually:

#### Backend Server:
```bash
# From project root directory
PYTHONPATH=$(pwd) python app/main.py
```

#### Frontend Server:
```bash
# From project root directory
cd chatbot-ui
npm start
```

## Viewing Logs

The application generates detailed logs to help with monitoring and troubleshooting. All logs are stored in the `logs/` directory:

### Backend/API Logs
These logs contain detailed information about API requests, database queries, and AI processing:

```bash
# View the entire backend log
cat logs/backend.log

# Watch backend logs in real-time (updates as new logs come in)
tail -f logs/backend.log

# See just the last 50 lines
tail -n 50 logs/backend.log

# Filter for errors only
grep ERROR logs/backend.log

# Filter for specific API endpoints
grep "process_query" logs/backend.log
```

### Frontend Logs
These logs show React application logs and build information:

```bash
# View frontend logs
cat logs/frontend.log

# Watch frontend logs in real-time
tail -f logs/frontend.log
```

### Application Logs
Internal application logs that may contain information not present in other log files:

```bash
# View application logs
cat logs/app.log
```

For real-time monitoring during application use, running `tail -f logs/backend.log` in a separate terminal window is recommended.

## Troubleshooting

- If the backend server closes unexpectedly, check that your OpenAI API key is set correctly
- Make sure all dependencies are installed: `pip install -r requirements.txt` and `cd chatbot-ui && npm install`
- If port 8000 or 3000 is already in use, stop the existing process or change the port in the configuration
- Check the logs (as described above) for detailed error messages
- If you see authentication errors in the logs, run `./setup_env.sh` to update your OpenAI API key

### Shell/Terminal Compatibility Issues

If you encounter errors like `python: command not found` when running the scripts in different terminals (e.g., iTerm vs. Terminal.app):

1. Make the scripts executable (you only need to do this once):
   ```bash
   chmod +x start_app.sh setup_env.sh
   ```

2. If you're using a virtual environment, make sure it's activated:
   ```bash
   source venv/bin/activate  # or venv311/bin/activate
   ```

3. Try running the script with explicit bash:
   ```bash
   bash start_app.sh
   ```

4. If issues persist, manually verify your Python installation:
   ```bash
   which python
   which python3
   ```
   
The scripts have been updated to automatically detect Python in common locations, including virtual environments.

