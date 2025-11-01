#!/bin/bash
# Quick start script for Coperniq Lead Generation Agent
# Activates virtual environment and runs the agent

set -e

# Activate virtual environment
source venv/bin/activate

# Run the agent
python3 agent/main.py
