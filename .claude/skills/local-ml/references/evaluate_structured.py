"""
Structured evaluation via local LLM — JSON output, batch processing.

Usage:
    from evaluate_structured import evaluate_batch
    results = evaluate_batch(items, prompt_template, model="qwen3:8b")
"""
import requests
import json
import re


def evaluate(prompt, model="qwen3:8b", temperature=0.1, max_tokens=2000):
    """Run evaluation prompt through local LLM. Returns text response."""
    resp = requests.post("http://localhost:11434/api/generate", json={
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": temperature, "num_predict": max_tokens}
    }, timeout=120)
    resp.raise_for_status()
    return resp.json()["response"]


def evaluate_json(prompt, model="qwen3:8b", temperature=0.1):
    """Run evaluation and parse JSON from response."""
    response = evaluate(prompt, model=model, temperature=temperature)

    # Try to extract JSON from response
    # Look for JSON block in markdown
    json_match = re.search(r'```json?\s*\n(.*?)\n```', response, re.DOTALL)
    if json_match:
        return json.loads(json_match.group(1))

    # Try direct parse
    try:
        return json.loads(response)
    except json.JSONDecodeError:
        pass

    # Try to find { ... } or [ ... ]
    for pattern in [r'\{[^{}]*\}', r'\[.*\]']:
        match = re.search(pattern, response, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                continue

    return {"raw_response": response, "parse_error": True}


def evaluate_batch(items, prompt_template, model="qwen3:8b",
                   temperature=0.1, show_progress=True):
    """Evaluate a batch of items using a prompt template.

    Args:
        items: list of dicts with data for the template
        prompt_template: string with {key} placeholders matching item keys
        model: Ollama model name
        temperature: generation temperature
        show_progress: print progress

    Returns:
        list of parsed JSON results
    """
    results = []
    total = len(items)

    for i, item in enumerate(items):
        prompt = prompt_template.format(**item)
        result = evaluate_json(prompt, model=model, temperature=temperature)
        result['_item_index'] = i
        results.append(result)

        if show_progress and (i + 1) % 10 == 0:
            print(f"  Evaluated {i + 1}/{total}")

    return results
