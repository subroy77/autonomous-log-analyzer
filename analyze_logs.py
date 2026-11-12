"""Command-line entry point for local log analysis."""

import argparse
import json
import sys

from core.log_analyzer_agent import LogAnalyzerAgent


def main(argv=None):
	parser = argparse.ArgumentParser(description="Analyze logs and build an incident timeline.")
	parser.add_argument("logfile", nargs="?", help="Log file to read; stdin is used when omitted.")
	parser.add_argument("--json", action="store_true", help="Print the complete report as JSON.")
	parser.add_argument("--llm", action="store_true", help="Add an OpenAI review (requires OPENAI_API_KEY).")
	parser.add_argument("--model", default="gpt-4o-mini", help="OpenAI model used with --llm.")
	args = parser.parse_args(argv)

	try:
		if args.logfile:
			with open(args.logfile, "r", encoding="utf-8") as source:
				log_text = source.read()
		else:
			log_text = sys.stdin.read()
		report = LogAnalyzerAgent(model=args.model).analyze(log_text, use_llm=args.llm)
	except (OSError, ValueError, RuntimeError) as exc:
		parser.error(str(exc))

	if args.json:
		print(json.dumps(report, indent=2, ensure_ascii=False))
	else:
		summary = report["assessment"]["summary"]
		print("Analyzed {entry_count} entries: {warning_count} warnings, {error_count} errors.".format(**summary))
		print("\nTimeline:")
		print(timeline_agent_text(report["incident"]["timeline"]))
		if report["incident"]["uncertainty"]:
			print("\nUncertainty:")
			for note in report["incident"]["uncertainty"]:
				print("- " + note)
	return 0


def timeline_agent_text(events):
	if not events:
		return "No events found."
	return "\n".join("{}: {}".format(event.get("timestamp") or "time unknown", event.get("message", "")) for event in events)


if __name__ == "__main__":
	sys.exit(main())

