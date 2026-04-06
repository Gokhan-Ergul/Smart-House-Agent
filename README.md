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
Smart-House-Agent/
├── src/smart_house_agent/   # LangGraph agents, tools, graphs, CLI
├── tests/                   # pytest
├── app/                     # FastAPI device simulator + dashboard
│   ├── static/
│   │   └── index.html
│   └── main.py
├── docs/                    # Project layout and guides
├── pyproject.toml           # Package metadata (pip install -e .)
├── requirements.txt
├── .env.example             # Copy to .env and set GOOGLE_API_KEY
├── home_status.json         # Runtime: device state (with API)
├── rules_operations.json    # Runtime: rules & routines
└── user_memory.txt          # Runtime: saved user profile text
```


#  Installation & Setup

## 1️ Clone the Repository

```bash
git clone https://github.com/Gokhan-Ergul/Smart-House-Agent.git
cd Smart-House-Agent
```

---

##  Set Up Virtual Environment

```bash
python -m venv .venv
```

### Activate the environment

**Windows:** `.venv\Scripts\activate`  

**Mac / Linux:** `source .venv/bin/activate`

---

## Install Dependencies

```bash
pip install -r requirements.txt
pip install -e .
```

Copy `.env.example` to `.env` and set `GOOGLE_API_KEY` (and optionally `SMART_HOUSE_API_URL`).

---

#  Usage Guide

This system requires **two components running simultaneously**.

---

##  Step 1: Start the Simulation Server

From the **`app`** folder, start FastAPI (keep this terminal open):

```bash
cd app
python main.py
```

###  Dashboard

Open **http://127.0.0.1:8000** in your browser to view device states.

---

##  Step 2: Run the Agent (same workflow as before, without Jupyter)

Open a **second** terminal at the **repository root** (venv activated, `pip install -e .` already done):

```bash
cd .\src\
```

```bash
python -m smart_house_agent.main "Turn on the light and lock the front door."
```

Other examples:

```bash
python -m smart_house_agent.main "What is the weather like today?"
python -m smart_house_agent.main "Create a Cinema Mode that turns off the lights and turns on the TV."
```

For **streaming debug output** (similar to stepping through the notebook), use `run_query` in Python after building the graph—see `src/smart_house_agent/runner.py` and `build_supervisor_application` in `src/smart_house_agent/graph/supervisor_graph.py`.

More detail on folders and files: **`docs/PROJECT_LAYOUT.md`**.

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
