# Copilot instructions

- Treat the repository root as the canonical project. The nested `autonomous-log-analyzer/` directory is an identical, untracked copy; do not edit it unless explicitly requested.
- Preserve compatibility with Python 3.9 and prefer the standard library unless a dependency is necessary.
- Keep log processing deterministic and offline by default. Never claim causality unless the log evidence supports it; make uncertainty explicit.
- Keep the CLI, assessment agent, timeline agent, and orchestration API consistent with one another.
- Add or update `unittest` coverage for behavior changes. Run the test suite with `.venv/bin/python -m unittest discover -s tests -v`.
- Never include secrets or raw API keys in source, tests, logs, or generated reports. Keep any LLM integration optional.