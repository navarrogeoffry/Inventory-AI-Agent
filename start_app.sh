#!/bin/bash

# Start Inventory AI Agent (both backend and frontend)
# This script starts both servers and keeps them running

# Define colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}Starting Inventory AI Agent...${NC}"

# Get the directory where this script is located
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"

# Check for OpenAI API key
if [ -f .env ]; then
  source .env
else
  if [ -z "$OPENAI_API_KEY" ]; then
    echo -e "${RED}ERROR: OpenAI API key not found.${NC}"
    echo -e "Please run ${BLUE}./setup_env.sh${NC} to set up your API key."
    exit 1
  fi
fi

# Check if API key is set
if [ -z "$OPENAI_API_KEY" ]; then
  echo -e "${RED}ERROR: OpenAI API key not set.${NC}"
  echo -e "Your .env file exists but the OPENAI_API_KEY is not set."
  echo -e "Please run ${BLUE}./setup_env.sh${NC} to set up your API key."
  exit 1
fi

# Create a trap to handle script termination
trap 'kill $(jobs -p) 2>/dev/null' EXIT

# Start the Python backend server with logging
echo -e "${BLUE}Starting backend server...${NC}"
mkdir -p logs
PYTHONPATH="$DIR" python app/main.py > logs/backend.log 2>&1 &
BACKEND_PID=$!

# Wait for the backend to initialize (longer wait time)
sleep 3

# Check if backend started successfully and get the port it's using
BACKEND_PORT=8000
if ps -p $BACKEND_PID > /dev/null; then
  echo -e "${GREEN}Backend server started successfully!${NC}"
  # Try to find which port the server is actually using from the logs
  if grep -q "Using port" logs/backend.log; then
    BACKEND_PORT=$(grep "Using port" logs/backend.log | grep -oE '[0-9]+' | tail -1)
    echo -e "Backend running on port: ${BLUE}$BACKEND_PORT${NC}"
  fi
  echo -e "Backend logs available at: ${BLUE}logs/backend.log${NC}"
else
  echo -e "${RED}ERROR: Backend server failed to start.${NC}"
  echo -e "Please check logs/backend.log for details."
  echo -e "Common issues:"
  echo -e "- Invalid OpenAI API key"
  echo -e "- Missing dependencies (run ${BLUE}pip install -r requirements.txt${NC})"
  exit 1
fi

# Start the React frontend server
echo -e "${BLUE}Starting frontend server...${NC}"
cd chatbot-ui

# Set environment variable for the backend port
export REACT_APP_BACKEND_PORT=$BACKEND_PORT

# Check if port 3000 is already in use
FRONTEND_PORT=3000
if lsof -Pi :$FRONTEND_PORT -sTCP:LISTEN -t >/dev/null ; then
  echo -e "${YELLOW}Port 3000 is already in use. Trying port 3001...${NC}"
  FRONTEND_PORT=3001
  # Try to start on port 3001
  PORT=$FRONTEND_PORT REACT_APP_BACKEND_PORT=$BACKEND_PORT npm start > ../logs/frontend.log 2>&1 &
else
  # Use default port 3000
  PORT=$FRONTEND_PORT REACT_APP_BACKEND_PORT=$BACKEND_PORT npm start > ../logs/frontend.log 2>&1 &
fi
FRONTEND_PID=$!

echo -e "\n${GREEN}Servers are starting...${NC}"
echo -e "Backend server: ${BLUE}http://localhost:$BACKEND_PORT${NC}"
echo -e "Frontend: ${BLUE}http://localhost:$FRONTEND_PORT${NC} (should open automatically in your browser)"
echo -e "Backend logs: ${BLUE}logs/backend.log${NC}"
echo -e "Frontend logs: ${BLUE}logs/frontend.log${NC}"
echo -e "\n${YELLOW}Press Ctrl+C to stop both servers${NC}"

# Monitoring loop - keep checking if servers are running
while true; do
  if ! ps -p $BACKEND_PID > /dev/null; then
    echo -e "${RED}Backend server stopped unexpectedly. Restarting...${NC}"
    cd "$DIR"
    PYTHONPATH="$DIR" python app/main.py >> logs/backend.log 2>&1 &
    BACKEND_PID=$!
    sleep 2
  fi
  
  if ! ps -p $FRONTEND_PID > /dev/null; then
    echo -e "${RED}Frontend server stopped unexpectedly. Restarting...${NC}"
    cd "$DIR/chatbot-ui"
    npm start >> ../logs/frontend.log 2>&1 &
    FRONTEND_PID=$!
    sleep 2
  fi
  
  sleep 5
done 