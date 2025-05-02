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

