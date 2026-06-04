# Validation Benchmark

This directory contains the experimental evaluation framework for the Smart-House-Agent system. It programmatically executes a set of benchmark prompts and measures task success, agent routing accuracy, token usage, and response latency.

## Files

- `validation_prompts.json`: The benchmark dataset containing 20 representative smart home prompts across 7 categories (device control, rule management, user memory, weather, general conversation, error handling, multi-step requests). Ground truth labels are included for automated evaluation.
- `validation_benchmark.py`: The Python script that runs the evaluation. It loads the LangGraph application directly to precisely measure token usage (via LangChain message metadata) and latency.
- `validation_results.csv`: The output file generated after running the benchmark. It contains aggregated statistics for each prompt over multiple runs.

## How to Run

1. Make sure your Python environment is active and all dependencies are installed (e.g., LangGraph, FastAPI, LangChain).
2. Ensure your `.env` file in the `Smart-House-Agent` root directory contains a valid `GEMINI_API_KEY`.
3. Start the FastAPI simulation server in a separate terminal:
   ```bash
   cd ../Smart-House-Agent/app
   python main.py
   ```
4. Run the benchmark script:
   ```bash
   cd ../overleaf_paper/validation
   python validation_benchmark.py
   ```
5. Wait for the execution to finish. The script will perform 3 runs per prompt to calculate average token usage and latency. It may take a few minutes.
6. Open `validation_results.csv` to view the generated metrics. Use these metrics to update `04-experimental-evaluation.tex` after any benchmark rerun.

## Important Note

The generated `validation_results.csv` contains the empirical measurements used by `04-experimental-evaluation.tex`. Re-run the benchmark after code, prompt, dependency, or model changes and update the LaTeX tables with the new CSV-derived values.
