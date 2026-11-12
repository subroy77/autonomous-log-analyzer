"""Parse log lines into a consistent, locally generated assessment."""

import json
import os
import re
from typing import Any, Dict, List, Optional


_TIMESTAMP_RE = re.compile(
    r"(?P<timestamp>\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}"
    r"(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})?)"
)
_LEVEL_RE = re.compile(r"\b(DEBUG|INFO|NOTICE|WARN(?:ING)?|ERROR|CRITICAL|FATAL)\b", re.I)
_COMPONENT_RE = re.compile(r"(?:\bcomponent=|\bservice=|\blogger=)([\w./:-]+)", re.I)
_BRACKET_COMPONENT_RE = re.compile(r"\[([A-Za-z_][\w./:-]*)\]")
_LEVEL_NAMES = {"WARN": "WARNING", "FATAL": "CRITICAL"}


def _level(value: Any) -> Optional[str]:
	if value is None:
		return None
	name = str(value).strip().upper()
	return _LEVEL_NAMES.get(name, name)


def _entry_from_json(raw: str, line_number: int) -> Optional[Dict[str, Any]]:
	try:
		value = json.loads(raw)
	except (TypeError, ValueError):
		return None
	if not isinstance(value, dict):
		return None

	timestamp = value.get("timestamp", value.get("time", value.get("@timestamp")))
	message = value.get("message", value.get("msg", raw))
	return {
		"line_number": line_number,
		"timestamp": str(timestamp) if timestamp is not None else None,
		"level": _level(value.get("level", value.get("severity"))),
		"component": value.get("component", value.get("service", value.get("logger"))),
		"message": str(message),
		"raw": raw,
	}


def _entry_from_text(raw: str, line_number: int) -> Dict[str, Any]:
	timestamp_match = _TIMESTAMP_RE.search(raw)
	level_match = _LEVEL_RE.search(raw)
	component_match = _COMPONENT_RE.search(raw) or _BRACKET_COMPONENT_RE.search(raw)
	return {
		"line_number": line_number,
		"timestamp": timestamp_match.group("timestamp") if timestamp_match else None,
		"level": _level(level_match.group(1)) if level_match else None,
		"component": component_match.group(1) if component_match else None,
		"message": raw.strip(),
		"raw": raw,
	}


def assess_log(
	log_text: str,
	model: str = "gpt-4o-mini",
	api_key: Optional[str] = None,
	use_llm: bool = False,
) -> Dict[str, Any]:
	"""Return parsed entries and issue counts; optionally request an LLM review.

	The default path is deterministic and offline. Passing ``api_key`` or setting
	``use_llm=True`` opts into the OpenAI API; the key is never written to disk.
	"""
	if not isinstance(log_text, str):
		raise TypeError("log_text must be a string")

	entries = []
	for line_number, raw in enumerate(log_text.splitlines(), 1):
		if not raw.strip():
			continue
		entry = _entry_from_json(raw, line_number) if raw.lstrip().startswith("{") else None
		entries.append(entry or _entry_from_text(raw, line_number))

	issues = []
	for entry in entries:
		if entry["level"] in ("WARNING", "ERROR", "CRITICAL"):
			issues.append({
				"line_number": entry["line_number"],
				"severity": entry["level"],
				"message": entry["message"],
			})

	result = {
		"entries": entries,
		"issues": issues,
		"summary": {
			"entry_count": len(entries),
			"warning_count": sum(entry["level"] == "WARNING" for entry in entries),
			"error_count": sum(entry["level"] in ("ERROR", "CRITICAL") for entry in entries),
			"issue_count": len(issues),
		},
	}

	if use_llm or api_key:
		resolved_key = api_key or os.getenv("OPENAI_API_KEY")
		if not resolved_key:
			raise ValueError("Set OPENAI_API_KEY or pass api_key when requesting LLM analysis.")
		try:
			from openai import OpenAI
		except ImportError as exc:
			raise RuntimeError("Install the optional OpenAI dependency from requirements.txt.") from exc

		client = OpenAI(api_key=resolved_key)
		response = client.chat.completions.create(
			model=model,
			messages=[
				{"role": "system", "content": "Assess logs conservatively. Do not infer causation without evidence."},
				{"role": "user", "content": "Review the following parsed log assessment and return concise JSON findings.\n"
				 + json.dumps(result, ensure_ascii=False)},
			],
			response_format={"type": "json_object"},
			temperature=0.1,
		)
		content = response.choices[0].message.content or "{}"
		try:
			result["llm_analysis"] = json.loads(content)
		except ValueError:
			result["llm_analysis"] = {"raw_response": content}

	return result

