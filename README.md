# autonomous-log-analyzer

A local-first log analyzer that extracts structured events, highlights warnings
and errors, and builds an evidence-conscious incident timeline. The default
analysis is deterministic and works offline; an optional OpenAI review can be
enabled when desired.

## Setup

Python 3.9 or newer is supported. Create and activate an isolated environment,
then install the optional LLM client:

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

## Use

Analyze a file, or pipe log text through standard input:

```sh
python analyze_logs.py application.log
cat application.log | python analyze_logs.py --json
```

For an additional OpenAI review, set `OPENAI_API_KEY` in the environment and
pass `--llm`. The key is not stored by the application. This step makes a
network request; local parsing and timeline generation do not.

The Python API is `core.log_analyzer_agent.LogAnalyzerAgent().analyze(log_text)`.
It returns an assessment and an incident object containing an ordered timeline,
explicitly evidenced causal links, possible (unconfirmed) cascades, confidence,
and uncertainty notes. Timestamp order and temporal precedence are not proof of
root cause.

## Tests

Run the standard-library test suite with:

```sh
python -m unittest discover -s tests -v
```
