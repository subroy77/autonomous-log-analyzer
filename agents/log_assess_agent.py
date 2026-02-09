import os
import openai

def assess_log(log_text, model="gpt-3.5-turbo", api_key=None):
	"""
	Accepts log text, calls LLM, and returns structured output.
	Args:
		log_text (str): The log text to analyze.
		model (str): The OpenAI model to use.
		api_key (str): The OpenAI API key. If None, uses OPENAI_API_KEY env var.
	Returns:
		dict: Structured output from the LLM.
	"""
	if api_key is None:
		api_key = os.getenv("OPENAI_API_KEY")
	if not api_key:
		raise ValueError("OpenAI API key must be provided or set in OPENAI_API_KEY env var.")
	openai.api_key = api_key

	prompt = (
		"You are a log assessment agent. Given the following log text, extract structured information such as "
		"timestamp, log level, component, message, and any detected error or warning patterns. "
		"Return the result as a JSON object with a list of log entries and a summary of detected issues.\n\n"
		f"Log text:\n{log_text}\n"
	)

	response = openai.ChatCompletion.create(
		model=model,
		messages=[{"role": "system", "content": "You are a helpful log assessment assistant."},
				 {"role": "user", "content": prompt}],
		temperature=0.2,
		max_tokens=800
	)

	# Try to extract JSON from the response
	import json
	content = response["choices"][0]["message"]["content"]
	try:
		structured = json.loads(content)
	except Exception:
		structured = {"raw_response": content}
	return structured

