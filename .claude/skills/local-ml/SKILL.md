---
name: local-ml
description: Run local ML models for embedding, evaluation, and clustering. Uses Ollama (nomic-embed-text, qwen3:8b) + Python (hdbscan, umap). Use when analyzing text at scale without API costs.
---

# Local ML

Run ML workloads locally on Apple Silicon. No API calls, no cost.

## Available Models

| Model | Purpose | Via | Size |
|-------|---------|-----|------|
| `nomic-embed-text-v1.5` | Text embeddings (768-dim) | sentence-transformers + MPS | 274 MB |
| `qwen3:8b` | Text evaluation/analysis | Ollama | 5.2 GB |

## Capabilities

### 1. Embed Text

Generate embeddings for text data. Use for similarity search, clustering, and classification.

```python
import requests
import numpy as np

def embed_texts(texts, model="nomic-embed-text"):
    """Embed a list of texts via Ollama. Returns numpy array of shape (n, 768)."""
    embeddings = []
    for text in texts:
        resp = requests.post("http://localhost:11434/api/embed", json={
            "model": model,
            "input": text
        })
        embeddings.append(resp.json()["embeddings"][0])
    return np.array(embeddings)
```

For large batches, use the batch helper in `references/embed_batch.py` which handles chunking, progress, and caching to Parquet.

### 2. Evaluate/Analyze Text

Use the local LLM for structured evaluation — scoring, classification, extraction.

```python
import requests

def evaluate(prompt, model="qwen3:8b"):
    """Run evaluation prompt through local LLM. Returns text response."""
    resp = requests.post("http://localhost:11434/api/generate", json={
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0.1, "num_predict": 2000}
    })
    return resp.json()["response"]
```

For structured output (JSON), use `references/evaluate_structured.py`.

### 3. Cluster & Discover Themes

Cluster embeddings to discover natural groupings in text data.

```python
import hdbscan
import umap

def cluster_embeddings(embeddings, min_cluster_size=10):
    """Reduce dimensions with UMAP, then cluster with HDBSCAN."""
    reducer = umap.UMAP(n_components=10, random_state=42)
    reduced = reducer.fit_transform(embeddings)
    clusterer = hdbscan.HDBSCAN(min_cluster_size=min_cluster_size)
    labels = clusterer.fit_predict(reduced)
    return labels, clusterer
```

## Prerequisites

- Ollama running: `ollama serve` (or auto-starts on macOS)
- Models pulled: `ollama pull nomic-embed-text && ollama pull qwen3:8b`
- Python packages: `pip3 install hdbscan umap-learn sentence-transformers scikit-learn`

## Usage Patterns

### Pattern: Embed → Cluster → Label

1. Embed texts with `nomic-embed-text`
2. Cluster with HDBSCAN
3. For each cluster, send 5 representative texts to `qwen3:8b` asking "what theme do these share?"
4. Result: data-driven taxonomy

### Pattern: Similarity-Based Scoring

1. Embed "gold standard" texts (e.g., best sales calls)
2. Embed all texts
3. Cosine similarity to gold standard = quality score
4. No rubric needed — learned from data

### Pattern: Selective Deep Analysis

1. Use embeddings to identify interesting subsets
2. Send only those (100-500) to Claude API for deep analysis
3. 100x cheaper than analyzing everything

## Hardware Notes

- M4 with 32GB can run embedding + 8B LLM simultaneously
- Embedding throughput: ~200 texts/sec for short texts, ~50/sec for paragraphs
- LLM throughput: ~30 tokens/sec generation on M4
- For very large batches (>100K), cache embeddings to Parquet
