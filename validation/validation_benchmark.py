"""
Validation Benchmark Script for Smart-House-Agent
==================================================

This script evaluates the Smart-House-Agent system by sending a set of
benchmark prompts and measuring:
  - Agent routing accuracy
  - Task success rate
  - Token usage (prompt, completion, total)
  - End-to-end latency, LLM latency, tool latency
  - Tool selection accuracy

Usage:
  1. Start the FastAPI server:
       cd app && python main.py

  2. Set the API key:
       set GOOGLE_API_KEY=your_key_here        (Windows)
       export GOOGLE_API_KEY=your_key_here      (Linux/macOS)

  3. Run the benchmark:
       python validation_benchmark.py

Results are saved to validation_results.csv in the same directory.

IMPORTANT: Do not hard-code API keys. The script reads GOOGLE_API_KEY
from environment variables exclusively.
"""

import json
import time
import asyncio
import csv
import os
from pathlib import Path
from statistics import mean, stdev

# Add the src directory to the python path so we can import the agent
import sys
_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(_ROOT / "src"))

try:
    from smart_house_agent.config import get_settings, get_llm
    from smart_house_agent.graph.supervisor_graph import build_supervisor_application
    from smart_house_agent.clients.home_api import HomeApiClient
    from langchain_core.messages import HumanMessage, AIMessage
except ImportError as e:
    print(f"Import error: {e}")
    print("Please make sure you run this from an environment where the "
          "smart_house_agent package is installed.")
    print("Run: pip install -e . from the Smart-House-Agent directory.")
    sys.exit(1)


import argparse

def check_api_key():
    """Ensure API key is set via environment variable."""
    key = os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY", "")
    if not key:
        print("ERROR: GOOGLE_API_KEY or GEMINI_API_KEY environment variable is not set.")
        print("Set it before running: set GOOGLE_API_KEY=your_key_here")
        sys.exit(1)
    os.environ.setdefault("GOOGLE_API_KEY", key)
    # Never print the key
    print("API key detected (from environment variable).")


async def run_single_prompt(graph, text, recursion_limit=15):
    """
    Run a single prompt through the agent graph.

    Returns:
        dict with keys:
            - route_taken: str or None
            - tokens: dict with prompt_tokens, completion_tokens, total_tokens
            - latency: float (end-to-end seconds)
            - response: str (final AI message)
            - tools_called: list of str
            - error: str or None
    """
    start_time = time.time()
    inputs = {"messages": [HumanMessage(content=text)]}

    route_taken = None
    tokens = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
    response_text = ""
    tools_called = []
    error_msg = None

    try:
        async for step in graph.astream(inputs, config={"recursion_limit": recursion_limit}):
            for agent_name, output in step.items():
                if agent_name == "refresh_context":
                    continue

                # Identify routing decision
                if "next" in output and output["next"] not in ("__end__", None):
                    if route_taken is None:
                        route_taken = output["next"]

                # Extract token usage and response from AIMessages
                if "messages" in output:
                    for msg in output["messages"]:
                        if isinstance(msg, AIMessage):
                            # Token usage
                            if hasattr(msg, "usage_metadata") and msg.usage_metadata:
                                tokens["prompt_tokens"] += msg.usage_metadata.get("input_tokens", 0)
                                tokens["completion_tokens"] += msg.usage_metadata.get("output_tokens", 0)
                                tokens["total_tokens"] += msg.usage_metadata.get("total_tokens", 0)

                            # Tool calls. LangGraph Supervisor v0.0.31 represents
                            # delegation as transfer_to_<agent> tool calls rather
                            # than an output["next"] field.
                            if hasattr(msg, "tool_calls") and msg.tool_calls:
                                for tc in msg.tool_calls:
                                    tool_name = tc.get("name", "unknown")
                                    if tool_name.startswith("transfer_to_"):
                                        route_taken = tool_name.removeprefix("transfer_to_")
                                    elif tool_name.startswith("transfer_back_to_"):
                                        continue
                                    else:
                                        tools_called.append(tool_name)

                            # Response text (last AI message)
                            if msg.content:
                                response_text = msg.content

    except Exception as e:
        error_msg = str(e)

    latency = time.time() - start_time
    actual_route = route_taken if route_taken else "supervisor"

    return {
        "route_taken": actual_route,
        "tokens": tokens,
        "latency": latency,
        "response": response_text[:200],  # Truncate for CSV
        "tools_called": tools_called,
        "error": error_msg,
    }


def reset_environment(settings, prompt_id=None):
    """Reset the external environment state (devices, memory, rules) to defaults, with specific test seeds."""
    # 1. Reset device status
    default_db = {
        "light": "off",
        "tv": "off",
        "curtain": "closed",
        "door_lock": "locked",
        "thermostat_mode": "off",
        "main_water_valve": "closed",
    }
    
    # State overrides to force agent action on specific tests
    if prompt_id == "T02":
        default_db["door_lock"] = "unlocked" # Force agent to lock it
    elif prompt_id == "T03" or prompt_id == "T17":
        default_db["light"] = "on" # Force agent to turn it off
    elif prompt_id == "T05":
        default_db["main_water_valve"] = "open" # Force agent to close it
        
    with open(settings.home_status_path, "w", encoding="utf-8") as f:
        json.dump(default_db, f)

    # 2. Reset user memory
    memory_content = ""
    if prompt_id == "T10":
        memory_content = "- User name is Gokhan\n- User prefers warm temperatures"
    
    with open(settings.user_memory_path, "w", encoding="utf-8") as f:
        f.write(memory_content)
    
    # 3. Reset rules and operations
    default_rules = {"rules": [], "operations": []}
    
    if prompt_id in ["T07", "T08"]:
        default_rules["operations"].append({
            "operation_name": "Cinema Mode",
            "home_operations": ["light off", "tv on", "curtain closed"]
        })
        default_rules["rules"].append("Cinema Mode: turn off lights, turn on TV, close curtains")
        
    with open(settings.rules_operations_path, "w", encoding="utf-8") as f:
        json.dump(default_rules, f, ensure_ascii=False, indent=2)

async def run_benchmark():
    """Execute the full benchmark suite."""
    parser = argparse.ArgumentParser(description="Smart-House-Agent Benchmark")
    parser.add_argument("--ids", nargs="+", help="Run specific test IDs. Example: --ids T10 T18", default=None)
    args = parser.parse_args()

    check_api_key()

    settings = get_settings()
    llm = get_llm(settings)
    api = HomeApiClient(settings.smart_house_api_url)

    prompts_path = Path(__file__).parent / "validation_prompts.json"
    with open(prompts_path, "r", encoding="utf-8") as f:
        prompts = json.load(f)

    if args.ids:
        prompts = [p for p in prompts if p["id"] in args.ids]
        if not prompts:
            print(f"Error: No tests found with IDs {args.ids}")
            return

    results = []
    runs_per_prompt = 3
    total_prompts = len(prompts)

    print(f"\n{'='*60}")
    print(f"Smart-House-Agent Validation Benchmark")
    print(f"{'='*60}")
    print(f"Prompts: {total_prompts}")
    print(f"Runs per prompt: {runs_per_prompt}")
    print(f"Total executions: {total_prompts * runs_per_prompt}")
    print(f"Model: {settings.gemini_model}")
    print(f"Temperature: {settings.gemini_temperature}")
    print(f"{'='*60}\n")

    for idx, item in enumerate(prompts, 1):
        prompt_id = item["id"]
        text = item["prompt"]
        expected_agent = item["expected_agent"]
        expected_tools = item.get("expected_tools", [])
        category = item["category"]

        print(f"[{idx}/{total_prompts}] {prompt_id}: {text}")

        run_latencies = []
        run_token_usage = []
        success_count = 0
        correct_route_count = 0
        correct_tool_count = 0
        all_errors = []

        for run in range(runs_per_prompt):
            reset_environment(settings, prompt_id)
            
            # Rebuild graph for each run to prevent any in-memory state leakage
            # (e.g. HomeStatusStore._data caching)
            graph = build_supervisor_application(settings, llm, api_client=api)
            
            result = await run_single_prompt(graph, text)

            run_latencies.append(result["latency"])
            run_token_usage.append(result["tokens"])

            # Check routing accuracy
            if result["route_taken"] == expected_agent:
                correct_route_count += 1

            # Check tool selection accuracy (if tools are expected)
            if expected_tools:
                actual_tool_names = set(result["tools_called"])
                expected_tool_names = set(expected_tools)
                if expected_tool_names.issubset(actual_tool_names):
                    correct_tool_count += 1
            else:
                # No tools expected; if no tools called, correct
                if not result["tools_called"]:
                    correct_tool_count += 1

            # Basic success heuristic: correct route + no error
            if result["route_taken"] == expected_agent and result["error"] is None:
                success_count += 1

            if result["error"]:
                all_errors.append(result["error"])

        # Aggregate statistics
        avg_latency = mean(run_latencies) if run_latencies else 0.0
        std_latency = stdev(run_latencies) if len(run_latencies) > 1 else 0.0
        min_latency = min(run_latencies) if run_latencies else 0.0
        max_latency = max(run_latencies) if run_latencies else 0.0

        avg_prompt_tokens = mean([t["prompt_tokens"] for t in run_token_usage]) if run_token_usage else 0
        avg_comp_tokens = mean([t["completion_tokens"] for t in run_token_usage]) if run_token_usage else 0
        avg_total_tokens = mean([t["total_tokens"] for t in run_token_usage]) if run_token_usage else 0

        res = {
            "id": prompt_id,
            "category": category,
            "prompt": text,
            "expected_agent": expected_agent,
            "expected_tools": ";".join(expected_tools),
            "success_rate": round(success_count / runs_per_prompt, 2),
            "route_accuracy": round(correct_route_count / runs_per_prompt, 2),
            "tool_accuracy": round(correct_tool_count / runs_per_prompt, 2),
            "avg_latency_s": round(avg_latency, 2),
            "min_latency_s": round(min_latency, 2),
            "max_latency_s": round(max_latency, 2),
            "std_latency_s": round(std_latency, 2),
            "avg_prompt_tokens": round(avg_prompt_tokens),
            "avg_output_tokens": round(avg_comp_tokens),
            "avg_total_tokens": round(avg_total_tokens),
            "errors": "; ".join(all_errors) if all_errors else "",
        }
        results.append(res)

        status = "PASS" if success_count == runs_per_prompt else (
            "PARTIAL" if success_count > 0 else "FAIL")
        print(f"  -> {status} | Success: {success_count}/{runs_per_prompt} | "
              f"Route: {correct_route_count}/{runs_per_prompt} | "
              f"Latency: {avg_latency:.2f}s | Tokens: {avg_total_tokens:.0f}")
        
        if status != "PASS":
            # Print debug info from the last run to help identify why it failed
            print(f"     [DEBUG] Last run route: '{result['route_taken']}' (Expected: '{expected_agent}')")
            print(f"     [DEBUG] Last run tools: {result['tools_called']} (Expected: {expected_tools})")
            if result['error']:
                print(f"     [DEBUG] Error: {result['error']}")

    # Export to CSV (Merge with existing if exists)
    csv_path = Path(__file__).parent / "validation_results.csv"
    
    merged_results = {}
    
    # 1. Read existing CSV data if it exists
    if csv_path.exists():
        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                merged_results[row["id"]] = row
                
    # 2. Update with the new test results
    for res in results:
        # Convert numeric values to strings for consistent dict merging, just in case
        merged_results[res["id"]] = {k: str(v) for k, v in res.items()}
        
    # 3. Sort by test ID to keep the table organized (T01, T02...)
    final_results = [merged_results[k] for k in sorted(merged_results.keys())]

    # 4. Write back the complete merged table
    if final_results:
        fieldnames = list(final_results[0].keys())
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(final_results)

    # Print summary
    print(f"\n{'='*60}")
    print("BENCHMARK SUMMARY")
    print(f"{'='*60}")

    total_success = sum(r["success_rate"] for r in results) / len(results)
    total_route_acc = sum(r["route_accuracy"] for r in results) / len(results)
    total_tool_acc = sum(r["tool_accuracy"] for r in results) / len(results)
    overall_latency = mean([r["avg_latency_s"] for r in results])
    overall_tokens = mean([r["avg_total_tokens"] for r in results])

    print(f"Task Success Rate:       {total_success*100:.1f}%")
    print(f"Agent Routing Accuracy:  {total_route_acc*100:.1f}%")
    print(f"Tool Selection Accuracy: {total_tool_acc*100:.1f}%")
    print(f"Avg End-to-End Latency:  {overall_latency:.2f}s")
    print(f"Avg Tokens per Query:    {overall_tokens:.0f}")
    print(f"\nResults saved to: {csv_path}")
    print(f"{'='*60}")


if __name__ == "__main__":
    asyncio.run(run_benchmark())
