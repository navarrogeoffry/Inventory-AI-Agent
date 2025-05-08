#!/bin/bash

# Setup environment for Inventory AI Agent
# This script helps set up the OpenAI API key

# Define colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}Inventory AI Agent - Environment Setup${NC}"
echo

# Check if .env file exists
if [ -f .env ]; then
  echo -e "${YELLOW}An .env file already exists. Do you want to overwrite it? (y/n)${NC}"
  read response
  if [[ ! "$response" =~ ^[Yy]$ ]]; then
    echo "Setup canceled. Your existing .env file was not modified."
    exit 0
  fi
fi

# Create logs directory if it doesn't exist
mkdir -p logs

# Ask for OpenAI API key
echo -e "${BLUE}Please enter your OpenAI API key:${NC}"
read api_key

# Validate the API key (basic format check)
if [[ ! "$api_key" =~ ^sk-[A-Za-z0-9]{32,}$ ]]; then
  echo -e "${YELLOW}Warning: The API key format doesn't look like a standard OpenAI key.${NC}"
  echo -e "Standard OpenAI keys start with 'sk-' followed by a string of characters."
  echo -e "Do you want to continue anyway? (y/n)"
  read continue_response
  if [[ ! "$continue_response" =~ ^[Yy]$ ]]; then
    echo "Setup canceled."
    exit 0
  fi
fi

# Create .env file
echo "# Inventory AI Agent Environment Variables" > .env
echo "" >> .env
echo "# OpenAI API key" >> .env
echo "OPENAI_API_KEY=\"$api_key\"" >> .env
echo "" >> .env
echo "# Database path (defaults to inventory.db in project root)" >> .env
echo "# DATABASE_URL=\"path/to/inventory.db\"" >> .env

# Make .env file readable only to the current user
chmod 600 .env

echo -e "${GREEN}Environment setup complete!${NC}"
echo "Your OpenAI API key has been saved to the .env file."
echo

# Test the API key
echo -e "${BLUE}Testing API key...${NC}"
export OPENAI_API_KEY="$api_key"

# Try to run a simple test using Python
if command -v python >/dev/null 2>&1; then
  python -c "
import os
try:
  import openai
  from openai import OpenAI
  client = OpenAI(api_key=os.environ.get('OPENAI_API_KEY'))
  print('OpenAI module is installed and API key is set.')
except ImportError:
  print('WARNING: OpenAI module is not installed. Run: pip install openai')
except Exception as e:
  print(f'ERROR testing API key: {str(e)}')
" 2>&1
else
  echo "Python not found. Cannot test API key."
fi

echo
echo -e "${YELLOW}Next steps:${NC}"
echo "1. Run ./start_app.sh to start the application"
echo "2. Access the web interface at http://localhost:3000"
echo 