"""
Batch embedding helper — handles chunking, progress, and Parquet caching.

Usage:
    from embed_batch import embed_to_parquet
    embed_to_parquet(texts, ids, output_path="embeddings.parquet", model="nomic-embed-text")
"""
import requests
import numpy as np
import os
import time


def embed_batch(texts, model="nomic-embed-text", batch_size=50, show_progress=True):
    """Embed texts in batches via Ollama. Returns numpy array (n, dim)."""
    all_embeddings = []
    total = len(texts)

    for i in range(0, total, batch_size):
        batch = texts[i:i + batch_size]
        batch_embeddings = []

        for text in batch:
            if not text or len(str(text).strip()) == 0:
                # Empty text — use zero vector
                batch_embeddings.append(None)
                continue

            try:
                resp = requests.post("http://localhost:11434/api/embed", json={
                    "model": model,
                    "input": str(text)[:2000]  # Truncate very long texts
                }, timeout=30)
                resp.raise_for_status()
                batch_embeddings.append(resp.json()["embeddings"][0])
            except Exception as e:
                print(f"  Error embedding text {i}: {e}")
                batch_embeddings.append(None)

        all_embeddings.extend(batch_embeddings)

        if show_progress and (i + batch_size) % 500 == 0:
            pct = min(100, round(100 * (i + batch_size) / total, 1))
            print(f"  Embedded {min(i + batch_size, total):,}/{total:,} ({pct}%)")

    # Replace None with zero vectors
    dim = None
    for e in all_embeddings:
        if e is not None:
            dim = len(e)
            break

    if dim is None:
        raise ValueError("No successful embeddings")

    result = np.array([e if e is not None else [0.0] * dim for e in all_embeddings], dtype=np.float32)
    return result


def embed_to_parquet(texts, ids, output_path, model="nomic-embed-text",
                     batch_size=50, resume=True):
    """Embed texts and save to Parquet with IDs. Supports resume from partial runs."""
    import pyarrow as pa
    import pyarrow.parquet as pq

    # Check for existing partial results
    start_idx = 0
    existing_ids = set()
    if resume and os.path.exists(output_path):
        try:
            existing = pq.read_table(output_path)
            existing_ids = set(existing.column('id').to_pylist())
            print(f"  Found {len(existing_ids):,} existing embeddings, resuming...")
        except Exception:
            pass

    # Filter to unprocessed
    todo_indices = [i for i, id_ in enumerate(ids) if id_ not in existing_ids]
    if not todo_indices:
        print("  All texts already embedded.")
        return output_path

    todo_texts = [texts[i] for i in todo_indices]
    todo_ids = [ids[i] for i in todo_indices]

    print(f"  Embedding {len(todo_texts):,} texts...")
    embeddings = embed_batch(todo_texts, model=model, batch_size=batch_size)

    # Build table
    dim = embeddings.shape[1]
    schema = pa.schema([
        ('id', pa.string()),
        ('embedding', pa.list_(pa.float32(), dim))
    ])

    rows = []
    for id_, emb in zip(todo_ids, embeddings):
        rows.append({'id': str(id_), 'embedding': emb.tolist()})

    table = pa.Table.from_pylist(rows, schema=schema)

    # Append to existing if resuming
    if existing_ids and os.path.exists(output_path):
        existing = pq.read_table(output_path)
        table = pa.concat_tables([existing, table])

    pq.write_table(table, output_path, compression='zstd')
    print(f"  Saved {len(table):,} embeddings to {output_path}")
    return output_path
