import json
import unittest

from agents.log_assess_agent import assess_log
from agents.timeline_agent import TimelineAgent
from core.log_analyzer_agent import LogAnalyzerAgent


class AssessLogTests(unittest.TestCase):
	def test_extracts_text_fields_and_issue_counts(self):
		text = (
			"2025-02-01T10:00:00Z INFO [api] server ready\n"
			"2025-02-01T10:00:01Z WARN [api] retrying request\n"
			"2025-02-01T10:00:02Z ERROR [db] connection failed"
		)
		result = assess_log(text)
		self.assertEqual(result["summary"], {
			"entry_count": 3,
			"warning_count": 1,
			"error_count": 1,
			"issue_count": 2,
		})
		self.assertEqual(result["entries"][0]["component"], "api")
		self.assertEqual(result["entries"][1]["level"], "WARNING")
		self.assertEqual(result["entries"][2]["level"], "ERROR")

	def test_parses_json_lines_and_skips_blank_lines(self):
		result = assess_log('\n{"time":"2025-02-01T10:00:00Z","severity":"fatal",'
			'"service":"worker","msg":"job failed"}\n')
		self.assertEqual(result["summary"]["entry_count"], 1)
		self.assertEqual(result["entries"][0]["level"], "CRITICAL")
		self.assertEqual(result["entries"][0]["component"], "worker")
		self.assertEqual(result["entries"][0]["message"], "job failed")

	def test_rejects_non_string_input(self):
		with self.assertRaises(TypeError):
			assess_log(None)


class TimelineAgentTests(unittest.TestCase):
	def test_sorts_timestamped_events_and_does_not_infer_causality_from_order(self):
		events = [
			{"line_number": 2, "timestamp": "2025-02-01T10:00:02Z", "level": "INFO", "message": "service started"},
			{"line_number": 1, "timestamp": "2025-02-01T10:00:01Z", "level": "INFO", "message": "service initialized"},
		]
		agent = TimelineAgent(events)
		self.assertEqual(agent.get_event_sequence(), ["service initialized", "service started"])
		self.assertEqual(agent.infer_causality(), [])
		self.assertEqual(agent.analyze()["confidence"], 1.0)

	def test_only_links_explicit_cause_to_matching_prior_event(self):
		events = [
			{"line_number": 1, "timestamp": "2025-02-01T10:00:00Z", "level": "ERROR", "message": "connection timeout"},
			{"line_number": 2, "timestamp": "2025-02-01T10:00:01Z", "level": "ERROR", "message": "request failed due to connection timeout"},
	]
		result = TimelineAgent(events).analyze()
		self.assertEqual(result["causal_chain"][0]["cause"], "E1")
		self.assertEqual(result["causal_chain"][0]["effect"], "E2")
		self.assertEqual(result["trigger_events"][0]["event_id"], "E1")
		self.assertEqual(result["possible_cascades"][0]["event_ids"], ["E2"])

	def test_missing_timestamps_are_reported_as_uncertain(self):
		result = TimelineAgent([{"line_number": 1, "message": "event"}]).analyze()
		self.assertEqual(result["confidence"], 0.0)
		self.assertTrue(any("timestamps are missing" in note for note in result["uncertainty"]))


class OrchestrationTests(unittest.TestCase):
	def test_orchestrator_returns_assessment_and_incident(self):
		report = LogAnalyzerAgent().analyze(
			'2025-02-01T10:00:00Z ERROR [api] request failed')
		self.assertEqual(report["assessment"]["summary"]["error_count"], 1)
		self.assertEqual(report["incident"]["timeline"][0]["event_id"], "E1")

	def test_assessment_is_json_serializable(self):
		report = LogAnalyzerAgent().analyze('{"level":"INFO","message":"ok"}')
		self.assertIsInstance(json.loads(json.dumps(report)), dict)


if __name__ == "__main__":
	unittest.main()