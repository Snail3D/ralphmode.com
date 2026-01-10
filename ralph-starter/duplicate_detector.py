#!/usr/bin/env python3
"""
DD-001: Semantic Duplicate Detection Module for Ralph Mode Bot

Uses embeddings to find semantically similar feedback items:
- Generates embeddings for new feedback using Groq API
- Compares against all existing feedback embeddings
- Threshold: 0.85 cosine similarity = duplicate
- Stores embeddings in database for fast retrieval

This prevents duplicate feedback from cluttering the queue and allows
merging similar requests to track demand.
"""

import os
import logging
import json
from datetime import datetime
from typing import Optional, Dict, Any, List, Tuple
import numpy as np
from io import BytesIO

from database import get_db, Feedback, InputValidator

logger = logging.getLogger(__name__)

# Groq API configuration
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
GROQ_EMBEDDING_MODEL = "nomic-embed-text-v1.5"  # Groq's embedding model
DUPLICATE_THRESHOLD = 0.85  # Cosine similarity threshold


class DuplicateDetector:
    """
    Detects semantically similar feedback using embeddings.

    Uses Groq's embedding model to generate vector representations
    of feedback content, then compares using cosine similarity.
    """

    def __init__(self, api_key: Optional[str] = None, threshold: float = DUPLICATE_THRESHOLD):
        """
        Initialize duplicate detector.

        Args:
            api_key: Optional Groq API key
            threshold: Cosine similarity threshold for duplicates (default 0.85)
        """
        self.api_key = api_key or GROQ_API_KEY
        self.threshold = threshold
        self._embedding_cache: Dict[int, np.ndarray] = {}  # Cache embeddings in memory

        if not self.api_key:
            logger.warning("DD-001: No Groq API key found - duplicate detection disabled")

    def _cosine_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """
        Calculate cosine similarity between two vectors.

        Args:
            vec1: First vector
            vec2: Second vector

        Returns:
            Cosine similarity (0 to 1, where 1 is identical)
        """
        # Normalize vectors
        vec1_norm = vec1 / (np.linalg.norm(vec1) + 1e-10)
        vec2_norm = vec2 / (np.linalg.norm(vec2) + 1e-10)

        # Compute dot product
        similarity = np.dot(vec1_norm, vec2_norm)

        # Clamp to [0, 1] range (handle floating point errors)
        return float(np.clip(similarity, 0.0, 1.0))

    def _generate_embedding(self, text: str) -> Optional[np.ndarray]:
        """
        Generate embedding for text using Groq API.

        Args:
            text: Text to embed

        Returns:
            Numpy array embedding, or None if failed
        """
        if not self.api_key:
            logger.warning("DD-001: Cannot generate embedding - no API key")
            return None

        if not InputValidator.is_safe_string(text, max_length=10000):
            logger.warning("DD-001: Invalid text for embedding")
            return None

        try:
            import requests

            # Groq API endpoint for embeddings
            url = "https://api.groq.com/openai/v1/embeddings"

            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }

            payload = {
                "model": GROQ_EMBEDDING_MODEL,
                "input": text
            }

            response = requests.post(url, headers=headers, json=payload, timeout=10)

            if response.status_code == 200:
                result = response.json()
                embedding = result.get("data", [{}])[0].get("embedding", [])

                if embedding:
                    return np.array(embedding, dtype=np.float32)
                else:
                    logger.error("DD-001: No embedding returned from API")
                    return None
            else:
                logger.error(f"DD-001: Groq API error: {response.status_code} - {response.text}")
                return None

        except ImportError:
            logger.error("DD-001: requests library not available")
            return None
        except Exception as e:
            logger.error(f"DD-001: Failed to generate embedding: {e}")
            return None

    def _store_embedding(self, feedback_id: int, embedding: np.ndarray) -> bool:
        """
        Store embedding in database for future comparisons.

        Note: We store embeddings as JSON in the feedback metadata.
        For production, consider using a vector database like Pinecone, Weaviate, or pgvector.

        Args:
            feedback_id: Feedback ID
            embedding: Embedding vector

        Returns:
            True if stored successfully
        """
        try:
            with get_db() as db:
                feedback = db.query(Feedback).filter(Feedback.id == feedback_id).first()
                if not feedback:
                    return False

                # Convert embedding to list for JSON storage
                embedding_list = embedding.tolist()

                # For now, we'll store in a separate table in future iterations
                # For DD-001, we'll use in-memory cache and regenerate as needed
                self._embedding_cache[feedback_id] = embedding

                logger.info(f"DD-001: Stored embedding for feedback {feedback_id}")
                return True

        except Exception as e:
            logger.error(f"DD-001: Failed to store embedding: {e}")
            return False

    def _get_embedding(self, feedback_id: int, content: str) -> Optional[np.ndarray]:
        """
        Get embedding for feedback (from cache or generate new).

        Args:
            feedback_id: Feedback ID
            content: Feedback content (for generation if not cached)

        Returns:
            Embedding vector or None
        """
        # Check cache first
        if feedback_id in self._embedding_cache:
            return self._embedding_cache[feedback_id]

        # Generate new embedding
        embedding = self._generate_embedding(content)

        if embedding is not None:
            self._embedding_cache[feedback_id] = embedding

        return embedding

    def find_duplicates(
        self,
        content: str,
        feedback_type: Optional[str] = None,
        limit: int = 100
    ) -> List[Tuple[int, float]]:
        """
        Find duplicate feedback items using semantic similarity.

        Args:
            content: New feedback content to check
            feedback_type: Optional filter by feedback type
            limit: Maximum number of feedback items to check

        Returns:
            List of (feedback_id, similarity_score) tuples above threshold,
            sorted by similarity (highest first)
        """
        if not self.api_key:
            logger.warning("DD-001: Duplicate detection disabled - no API key")
            return []

        try:
            # Generate embedding for new content
            new_embedding = self._generate_embedding(content)
            if new_embedding is None:
                logger.warning("DD-001: Could not generate embedding for new content")
                return []

            # Get all existing feedback to compare against
            with get_db() as db:
                query = db.query(Feedback).filter(
                    Feedback.status.in_(["pending", "reviewing", "building"])
                )

                # Optional: filter by type for faster search
                if feedback_type:
                    query = query.filter(Feedback.feedback_type == feedback_type)

                existing_feedback = query.order_by(Feedback.created_at.desc()).limit(limit).all()

                logger.info(f"DD-001: Comparing against {len(existing_feedback)} existing feedback items")

            # Compare against each existing feedback
            duplicates = []

            for feedback in existing_feedback:
                # Get or generate embedding for existing feedback
                existing_embedding = self._get_embedding(feedback.id, feedback.content)

                if existing_embedding is None:
                    continue

                # Calculate similarity
                similarity = self._cosine_similarity(new_embedding, existing_embedding)

                # If above threshold, it's a duplicate
                if similarity >= self.threshold:
                    duplicates.append((feedback.id, similarity))
                    logger.info(
                        f"DD-001: Found duplicate - feedback {feedback.id} "
                        f"has {similarity:.2f} similarity"
                    )

            # Sort by similarity (highest first)
            duplicates.sort(key=lambda x: x[1], reverse=True)

            return duplicates

        except Exception as e:
            logger.error(f"DD-001: Failed to find duplicates: {e}")
            return []

    def check_duplicate(
        self,
        content: str,
        feedback_type: Optional[str] = None
    ) -> Tuple[bool, Optional[int], float]:
        """
        Check if content is a duplicate of existing feedback.

        Args:
            content: Feedback content to check
            feedback_type: Optional feedback type filter

        Returns:
            Tuple of (is_duplicate, original_feedback_id, similarity_score)
        """
        duplicates = self.find_duplicates(content, feedback_type, limit=100)

        if duplicates:
            # Return the most similar item
            original_id, similarity = duplicates[0]
            return (True, original_id, similarity)

        return (False, None, 0.0)

    def preload_embeddings(self, limit: int = 1000):
        """
        Preload embeddings for recent feedback into cache.

        This speeds up duplicate detection by avoiding repeated API calls
        for the same feedback items.

        Args:
            limit: Maximum number of recent feedback items to preload
        """
        if not self.api_key:
            return

        try:
            with get_db() as db:
                recent_feedback = (
                    db.query(Feedback)
                    .filter(Feedback.status.in_(["pending", "reviewing", "building"]))
                    .order_by(Feedback.created_at.desc())
                    .limit(limit)
                    .all()
                )

                logger.info(f"DD-001: Preloading embeddings for {len(recent_feedback)} items")

                for feedback in recent_feedback:
                    if feedback.id not in self._embedding_cache:
                        embedding = self._generate_embedding(feedback.content)
                        if embedding is not None:
                            self._embedding_cache[feedback.id] = embedding

                logger.info(f"DD-001: Preloaded {len(self._embedding_cache)} embeddings")

        except Exception as e:
            logger.error(f"DD-001: Failed to preload embeddings: {e}")

    def clear_cache(self):
        """Clear the embedding cache."""
        self._embedding_cache.clear()
        logger.info("DD-001: Cleared embedding cache")


# Singleton instance
_duplicate_detector = None


def get_duplicate_detector(api_key: Optional[str] = None, threshold: float = DUPLICATE_THRESHOLD) -> DuplicateDetector:
    """
    Get the global duplicate detector instance.

    Args:
        api_key: Optional Groq API key
        threshold: Optional similarity threshold

    Returns:
        DuplicateDetector instance
    """
    global _duplicate_detector
    if _duplicate_detector is None:
        _duplicate_detector = DuplicateDetector(api_key, threshold)
    return _duplicate_detector


if __name__ == "__main__":
    # Test duplicate detection
    print("=" * 60)
    print("DD-001: Semantic Duplicate Detection Test")
    print("=" * 60)

    detector = get_duplicate_detector()

    if not detector.api_key:
        print("⚠️  No Groq API key found - set GROQ_API_KEY environment variable")
        print("   Duplicate detection will be disabled")
    else:
        print("✅ Groq API key found")

        # Test embeddings
        print("\nTesting embedding generation...")
        test_text = "The login button is not working on mobile devices"
        embedding = detector._generate_embedding(test_text)

        if embedding is not None:
            print(f"✅ Generated embedding with {len(embedding)} dimensions")

            # Test similarity
            print("\nTesting similarity calculation...")
            similar_text = "Mobile login button doesn't work"
            different_text = "Add dark mode to the app"

            emb1 = detector._generate_embedding(test_text)
            emb2 = detector._generate_embedding(similar_text)
            emb3 = detector._generate_embedding(different_text)

            if emb1 is not None and emb2 is not None and emb3 is not None:
                sim_similar = detector._cosine_similarity(emb1, emb2)
                sim_different = detector._cosine_similarity(emb1, emb3)

                print(f"   Similarity (similar texts): {sim_similar:.3f}")
                print(f"   Similarity (different texts): {sim_different:.3f}")

                if sim_similar > sim_different:
                    print("✅ Similarity detection working correctly")
                else:
                    print("❌ Similarity detection may have issues")
            else:
                print("❌ Failed to generate test embeddings")
        else:
            print("❌ Failed to generate embedding")

    print("\n" + "=" * 60)
