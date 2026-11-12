"""Build chronological incident timelines without overstating causality."""

import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple


_CAUSE_RE = re.compile(r"\b(?:caused by|due to|because of|triggered by)\s+([^.;]+)", re.I)


def _parse_timestamp(value: Any) -> Optional[datetime]:
	if not value:
		return None
	text = str(value).strip()
	try:
		parsed = datetime.fromisoformat(text[:-1] + "+00:00" if text.endswith("Z") else text)
	except ValueError:
		return None
	if parsed.tzinfo is None:
		parsed = parsed.replace(tzinfo=timezone.utc)
	return parsed.astimezone(timezone.utc)


class TimelineAgent:
	"""Sort parsed events and report only evidence-backed causal links."""

	def __init__(self, log_events: List[Dict[str, Any]], pattern_findings: Optional[List[Dict[str, Any]]] = None):
		self.log_events = list(log_events)
		self.pattern_findings = list(pattern_findings or [])
		self.log_events.sort(key=self._sort_key)

	@staticmethod
	def _sort_key(event: Dict[str, Any]) -> Tuple[int, Any, int]:
		timestamp = _parse_timestamp(event.get("timestamp"))
		line_number = event.get("line_number", 0)
		return (0, timestamp, int(line_number or 0)) if timestamp else (1, datetime.max.replace(tzinfo=timezone.utc), int(line_number or 0))

	def get_timeline(self) -> List[Dict[str, Any]]:
		return list(self.log_events)

	def get_event_sequence(self) -> List[str]:
		return [str(event.get("message", "")) for event in self.log_events]

	def infer_causality(self) -> List[Dict[str, Any]]:
		"""Return causal links only when a later message explicitly names an earlier event."""
		links = []
		for index, event in enumerate(self.log_events):
			message = str(event.get("message", ""))
			match = _CAUSE_RE.search(message)
			caused_by = None
			if match:
				reference = match.group(1).strip().lower()
				for candidate in reversed(self.log_events[:index]):
					if reference and reference in str(candidate.get("message", "")).lower():
						caused_by = candidate
						break
			if caused_by is not None:
				links.append({"event": event, "caused_by": caused_by, "evidence": message, "confidence": 0.85})
		return links

	def analyze(self) -> Dict[str, Any]:
		"""Return a structured timeline, possible triggers, cascades, and uncertainty."""
		timeline = []
		for index, event in enumerate(self.log_events, 1):
			timeline.append({"event_id": "E{}".format(index), **event})
		event_positions = {id(event): index for index, event in enumerate(self.log_events, 1)}

		errors = [item for item in timeline if item.get("level") in ("ERROR", "CRITICAL")]
		causal_chain = []
		for link in self.infer_causality():
			causal_chain.append({
				"cause": "E{}".format(event_positions[id(link["caused_by"])]),
				"effect": "E{}".format(event_positions[id(link["event"])]),
				"evidence": link["evidence"],
				"confidence": link["confidence"],
			})

		trigger_events = []
		possible_cascades = []
		if errors:
			first_error = errors[0]
			trigger_events.append({
				"event_id": first_error["event_id"],
				"confidence": 0.35,
				"rationale": "Earliest logged error; temporal precedence alone does not establish root cause.",
			})
			if len(errors) > 1:
				possible_cascades.append({
					"after_event_id": first_error["event_id"],
					"event_ids": [item["event_id"] for item in errors[1:]],
					"confidence": 0.25,
					"rationale": "Later errors may be related, but the available log sequence does not prove a cascade.",
				})

		uncertainty = []
		if any(_parse_timestamp(event.get("timestamp")) is None for event in self.log_events):
			uncertainty.append("Some timestamps are missing or unsupported; their relative order follows input order.")
		if not causal_chain:
			uncertainty.append("No explicit cause-and-effect statement could be matched to an earlier event.")
		if self.pattern_findings:
			uncertainty.append("Pattern findings are signals for review, not proof of root cause.")

		parsed_timestamps = sum(_parse_timestamp(event.get("timestamp")) is not None for event in self.log_events)
		ordering_confidence = (parsed_timestamps / len(self.log_events)) if self.log_events else 0.0
		return {
			"timeline": timeline,
			"causal_chain": causal_chain,
			"trigger_events": trigger_events,
			"possible_cascades": possible_cascades,
			"confidence": round(ordering_confidence, 2),
			"confidence_scope": "timestamp-based ordering, not root-cause certainty",
			"uncertainty": uncertainty,
		}

	def summarize_timeline(self) -> str:
		if not self.log_events:
			return "No events found."
		lines = []
		for event in self.log_events:
			timestamp = event.get("timestamp") or "time unknown"
			lines.append("{}: {}".format(timestamp, event.get("message", "")))
		return "\n".join(lines)
