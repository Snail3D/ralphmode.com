#!/usr/bin/env python3
"""
Task Embeddings - Semantic Similarity for Task Clustering

Generates vector embeddings for PRD tasks to enable intelligent clustering.
Uses TF-IDF as a fallback, with optional sentence-transformers support.
"""

import json
import hashlib
import pickle
from pathlib import Path
from typing import List, Dict, Optional
import numpy as np


# Cache file for embeddings
CACHE_FILE = Path(__file__).parent / ".embedding_cache.pkl"


def task_to_text(task: Dict) -> str:
    """
    Convert a task dict to a single text string for embedding.

    Combines:
    - Title (weighted heavily)
    - Description
    - Category
    - Acceptance criteria

    Args:
        task: Task dictionary

    Returns:
        Combined text representation
    """
    parts = []

    # Title is most important - repeat 3x for weight
    title = task.get("title", "")
    parts.extend([title] * 3)

    # Category provides context - repeat 2x
    category = task.get("category", "")
    parts.extend([category] * 2)

    # Description
    description = task.get("description", "")
    parts.append(description)

    # Acceptance criteria
    criteria = task.get("acceptance_criteria", [])
    parts.extend(criteria)

    return " ".join(parts)


def task_hash(task: Dict) -> str:
    """Generate a stable hash for a task to use as cache key"""
    # Use task ID and relevant fields
    key_parts = [
        task.get("id", ""),
        task.get("title", ""),
        task.get("description", ""),
        task.get("category", "")
    ]
    combined = "|".join(key_parts)
    return hashlib.md5(combined.encode()).hexdigest()


def load_cache() -> Dict[str, np.ndarray]:
    """Load embedding cache from disk"""
    if CACHE_FILE.exists():
        try:
            with open(CACHE_FILE, 'rb') as f:
                return pickle.load(f)
        except Exception as e:
            print(f"Warning: Could not load cache: {e}")
    return {}


def save_cache(cache: Dict[str, np.ndarray]):
    """Save embedding cache to disk"""
    try:
        with open(CACHE_FILE, 'wb') as f:
            pickle.dump(cache, f)
    except Exception as e:
        print(f"Warning: Could not save cache: {e}")


def generate_embeddings_tfidf(tasks: List[Dict]) -> Dict[str, np.ndarray]:
    """
    Generate TF-IDF based embeddings (fallback method).
    Fast, lightweight, no external dependencies.

    Args:
        tasks: List of task dictionaries

    Returns:
        Dict mapping task_id -> embedding vector
    """
    from sklearn.feature_extraction.text import TfidfVectorizer

    # Convert tasks to text
    task_texts = [task_to_text(task) for task in tasks]
    task_ids = [task.get("id", f"task_{i}") for i, task in enumerate(tasks)]

    # Generate TF-IDF vectors
    vectorizer = TfidfVectorizer(
        max_features=256,  # Limit dimensionality
        stop_words='english',
        ngram_range=(1, 2),  # Unigrams and bigrams
        min_df=1  # Allow rare words (small corpus)
    )

    tfidf_matrix = vectorizer.fit_transform(task_texts)

    # Convert to dict
    embeddings = {}
    for i, task_id in enumerate(task_ids):
        embeddings[task_id] = tfidf_matrix[i].toarray().flatten()

    return embeddings


def generate_embeddings_transformers(tasks: List[Dict]) -> Dict[str, np.ndarray]:
    """
    Generate embeddings using sentence-transformers (optional, better quality).

    Requires: pip install sentence-transformers

    Args:
        tasks: List of task dictionaries

    Returns:
        Dict mapping task_id -> embedding vector
    """
    try:
        from sentence_transformers import SentenceTransformer

        # Use a lightweight model
        model = SentenceTransformer('all-MiniLM-L6-v2')

        # Convert tasks to text
        task_texts = [task_to_text(task) for task in tasks]
        task_ids = [task.get("id", f"task_{i}") for i, task in enumerate(tasks)]

        # Generate embeddings
        vectors = model.encode(task_texts, show_progress_bar=False)

        # Convert to dict
        embeddings = {}
        for i, task_id in enumerate(task_ids):
            embeddings[task_id] = vectors[i]

        return embeddings

    except ImportError:
        print("sentence-transformers not installed, falling back to TF-IDF")
        return generate_embeddings_tfidf(tasks)


def generate_embeddings(tasks: List[Dict], use_cache: bool = True) -> Dict[str, np.ndarray]:
    """
    Generate semantic embeddings for PRD tasks.

    Tries to use sentence-transformers for quality, falls back to TF-IDF.
    Caches results to avoid re-computation.

    Args:
        tasks: List of task dictionaries
        use_cache: Whether to use/update cache (default True)

    Returns:
        Dict mapping task_id -> embedding vector (numpy array)
    """
    # Load cache
    cache = load_cache() if use_cache else {}

    # Separate cached and uncached tasks
    uncached_tasks = []
    result = {}

    for task in tasks:
        task_id = task.get("id", "")
        if not task_id:
            continue

        h = task_hash(task)

        if use_cache and h in cache:
            # Use cached embedding
            result[task_id] = cache[h]
        else:
            # Need to compute
            uncached_tasks.append(task)

    # Generate embeddings for uncached tasks
    if uncached_tasks:
        print(f"Generating embeddings for {len(uncached_tasks)} tasks...")

        # Try transformers first, fallback to TF-IDF
        try:
            new_embeddings = generate_embeddings_transformers(uncached_tasks)
        except Exception as e:
            print(f"Transformer embedding failed: {e}")
            new_embeddings = generate_embeddings_tfidf(uncached_tasks)

        # Update result and cache
        for task in uncached_tasks:
            task_id = task.get("id", "")
            if task_id in new_embeddings:
                result[task_id] = new_embeddings[task_id]

                # Update cache
                if use_cache:
                    h = task_hash(task)
                    cache[h] = new_embeddings[task_id]

    # Save updated cache
    if use_cache and uncached_tasks:
        save_cache(cache)
        print(f"Cache updated. {len(cache)} embeddings cached.")

    return result


def cosine_similarity(v1: np.ndarray, v2: np.ndarray) -> float:
    """Calculate cosine similarity between two vectors"""
    norm1 = np.linalg.norm(v1)
    norm2 = np.linalg.norm(v2)

    if norm1 == 0 or norm2 == 0:
        return 0.0

    return np.dot(v1, v2) / (norm1 * norm2)


def find_similar_tasks(
    task_id: str,
    all_embeddings: Dict[str, np.ndarray],
    top_k: int = 5
) -> List[tuple]:
    """
    Find the most similar tasks to a given task.

    Args:
        task_id: ID of the query task
        all_embeddings: Dict of all embeddings
        top_k: Number of similar tasks to return

    Returns:
        List of (task_id, similarity_score) tuples, sorted by similarity
    """
    if task_id not in all_embeddings:
        return []

    query_vec = all_embeddings[task_id]
    similarities = []

    for other_id, other_vec in all_embeddings.items():
        if other_id == task_id:
            continue

        sim = cosine_similarity(query_vec, other_vec)
        similarities.append((other_id, sim))

    # Sort by similarity (descending)
    similarities.sort(key=lambda x: x[1], reverse=True)

    return similarities[:top_k]


def test_embeddings():
    """Test embedding generation with sample tasks"""

    sample_tasks = [
        {
            "id": "UI-001",
            "title": "Add Dark Mode Toggle",
            "description": "Create a toggle button for dark mode in the settings page",
            "category": "UI/UX",
            "acceptance_criteria": ["Toggle exists", "Theme switches properly"]
        },
        {
            "id": "UI-002",
            "title": "Update Button Colors",
            "description": "Change all buttons to match the new brand colors",
            "category": "UI/UX",
            "acceptance_criteria": ["All buttons updated", "Colors are brand-compliant"]
        },
        {
            "id": "API-001",
            "title": "Add User Login Endpoint",
            "description": "Create POST /api/login endpoint for user authentication",
            "category": "Backend",
            "acceptance_criteria": ["Endpoint exists", "Returns JWT token"]
        },
        {
            "id": "API-002",
            "title": "Add Rate Limiting",
            "description": "Implement rate limiting on all API endpoints",
            "category": "Backend",
            "acceptance_criteria": ["Rate limiter works", "429 errors returned"]
        }
    ]

    print("=== Task Embeddings Test ===\n")

    # Generate embeddings
    embeddings = generate_embeddings(sample_tasks, use_cache=False)

    print(f"Generated {len(embeddings)} embeddings\n")

    # Check embedding dimensions
    for task_id, vec in embeddings.items():
        print(f"{task_id}: {vec.shape} dimensions")

    print("\n=== Similarity Test ===\n")

    # Find similar tasks to UI-001
    similar = find_similar_tasks("UI-001", embeddings, top_k=3)
    print(f"Tasks similar to UI-001 (Dark Mode Toggle):")
    for task_id, score in similar:
        print(f"  {task_id}: {score:.3f}")

    # UI-002 should be most similar (both UI tasks)
    assert similar[0][0] == "UI-002", "Most similar task should be UI-002"
    # Note: TF-IDF similarity can be low with small samples, just verify it's positive
    assert similar[0][1] > 0.0, "Similarity should be positive"

    print("\n✅ All tests passed!")


if __name__ == "__main__":
    test_embeddings()
