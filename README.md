# Smart-House-Agent

This project implements an **intelligent, multi-agent smart home automation system** using **LangGraph**.
It utilizes a **hierarchical Supervisor–Worker architecture** to interpret natural language commands, manage physical device states, enforce user-defined automation rules, and maintain personalized user memory.

---

##  Key Features

###  Natural Language Control
Control devices with complex commands like:  
> *"Turn on the lights and lock the door."*

---

###  Hierarchical Agent Architecture
A **central Supervisor** intelligently routes tasks to specialized agents **only when needed**, reducing unnecessary computation.

---

###  Persistent User Memory
The system learns and saves user details such as:
- *"My name is Sadık"*
- *"Answer me like a brother"*

All stored persistently in a local `user_memory.txt` file.
---

### Custom Rules & Routines
Users can define automation macros dynamically:
> *"Create 'Movie Mode' that turns off lights and turns on the TV."*

These are stored and managed via a structured rules database.

---

###  Real-time Context Awareness
Integrated **Weather Tool** allows context-based decisions:
- Checks rain status before opening windows
- Adjusts actions based on real-world conditions

---

###  Simulation Environment
A **FastAPI server** provides a visual dashboard to simulate and monitor smart home device states — no physical hardware required.

---

## System Architecture

The system is built on **LangGraph** with a **Supervisor Node** that delegates tasks to specialized agents:

###  Home Operations Agent 
**Role:** The *Doer*  

**Responsibilities:**
- Controls physical devices:
  - Lights
  - TV
  - Curtains
  - Locks
  - Thermostat
  - Water Valve  

---

###  Rule Operations Agent
**Role:** The *planner*  
**Responsibilities:**
- Manages `rules_operations.json`
- Defines, updates, and deletes automation scenarios
- Handles routines and behavioral rules

---

###  User Memory Agent
**Role:** The *librarian*  
**Responsibilities:**
- Extracts factual user information from conversations
- Saves long-term data into `user_memory.txt`

---

###  Weather Tool (Direct Tool)
**Role:** Context provider  
**Details:**
- Uses **OpenMeteo API**
- Supplies real-time weather data directly to the Supervisor
- Enables smarter, environment-aware decisions

---

##  Project Structure

```plaintext
TEZ/
├── .venv/                  # Python virtual environment
├── app/                    # Simulation API Server
│   ├── static/
│   │   └── index.html      # Web Dashboard for viewing device states
│   └── main.py             # FastAPI server script
├── home_status.json        # Shared "Database" (Syncs Agent & API state)
├── projectv2.ipynb         # Main Application Logic (LangGraph Agents)
├── rules_operations.json   # Stores user-defined automation rules
├── user_memory.txt         # Stores long-term user info
├── requirements.txt        # Project dependencies
└── .env                    # Environment variables (API Keys)


#  Installation & Setup

## 1️ Clone the Repository
git clone https://github.com/Gokhan-Ergul/Smart-House-Agent.git
cd TEZ

---

##  Set Up Virtual Environment
python -m venv .venv

### Activate the environment

Windows  
.venv\Scripts\activate  

Mac / Linux  
source .venv/bin/activate  

---

## Install Dependencies
pip install -r requirements.txt

---

#  Usage Guide

This system requires **two components running simultaneously**.

---

##  Step 1: Start the Simulation Server

Navigate to the app folder and start FastAPI:

cd app  
python main.py

###  Dashboard
Open your browser at:
http://127.0.0.1:8000  

to view live device states.

---

##  Step 2: Run the Agent System

Open `projectv2.ipynb` in VS Code or Jupyter Notebook  
Run all initialization cells  

Use the `run_query` function to interact with the system:

run_query("Turn on the light and lock the front door.", graph)  

run_query("Create a 'Cinema Mode' that turns off the lights and turns on the TV.", graph)  

run_query("It's getting dark, should I close the curtains?", graph)  

---

# Technologies Used

- LangChain & LangGraph – Multi-agent orchestration  
- Google Gemini (gemini-2.5-flash) – Core LLM  
- FastAPI – Device simulation server  
- OpenMeteo API – Real-time weather data  

---

#  Authors
- Gökhan Ergül
- Sadık Can Barut  
