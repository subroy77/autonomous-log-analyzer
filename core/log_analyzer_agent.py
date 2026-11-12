"""Coordinate log assessment and timeline reconstruction."""

from typing import Any, Dict

from agents.log_assess_agent import assess_log
from agents.timeline_agent import TimelineAgent


class LogAnalyzerAgent:
	"""Run the deterministic assessment and timeline stages for raw logs."""

	def __init__(self, model: str = "gpt-4o-mini") -> None:
		self.model = model

	def analyze(self, log_text: str, use_llm: bool = False) -> Dict[str, Any]:
		assessment = assess_log(log_text, model=self.model, use_llm=use_llm)
		timeline = TimelineAgent(assessment["entries"], assessment["issues"]).analyze()
		return {"assessment": assessment, "incident": timeline}


def analyze_logs(log_text: str, use_llm: bool = False) -> Dict[str, Any]:
	"""Convenience function for applications that do not need an agent instance."""
	return LogAnalyzerAgent().analyze(log_text, use_llm=use_llm)

