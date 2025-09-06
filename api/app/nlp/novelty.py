import numpy as np
from typing import List, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_
import structlog

from app.db.models import Document
from sqlalchemy import true
from app.nlp.pipeline import nlp_pipeline

logger = structlog.get_logger()

class NoveltyCalculator:
    def __init__(self):
        self.lookback_days = 30
        self.min_similarity_threshold = 0.3
    
    def calculate_novelty(
        self,
        text: str,
        ticker: str,
        published_at: datetime,
        db: Session,
        embedding: Optional[np.ndarray] = None
    ) -> float:
        """
        Calculate novelty score for a document based on similarity to recent documents
        Returns a score between 0 (not novel) and 1 (very novel)
        """
        
        if embedding is None:
            embedding = nlp_pipeline.generate_embedding(text)
        
        # Get recent documents for the same ticker
        lookback_date = published_at - timedelta(days=self.lookback_days)
        
        recent_docs = db.query(Document).filter(
            and_(
                Document.published_at >= lookback_date,
                Document.published_at < published_at,
                Document.meta['tickers'].contains([ticker]) if ticker else true()
            )
        ).limit(100).all()
        
        if not recent_docs:
            # No recent documents, maximum novelty
            return 1.0
        
        # Calculate cosine similarity with recent documents
        similarities = []
        
        for doc in recent_docs:
            if doc.embedding is not None:
                # Calculate cosine similarity
                doc_embedding = np.array(doc.embedding)
                similarity = self._cosine_similarity(embedding, doc_embedding)
                similarities.append(similarity)
        
        if not similarities:
            return 1.0
        
        # Calculate novelty score
        # Higher similarity means lower novelty
        max_similarity = max(similarities)
        avg_similarity = np.mean(similarities)
        
        # Weighted combination of max and average
        combined_similarity = 0.7 * max_similarity + 0.3 * avg_similarity
        
        # Convert to novelty score (inverse of similarity)
        novelty = 1.0 - combined_similarity
        
        # Apply non-linear transformation for better distribution
        novelty = self._transform_novelty_score(novelty)
        
        logger.info(
            "Calculated novelty score",
            ticker=ticker,
            novelty=novelty,
            max_similarity=max_similarity,
            avg_similarity=avg_similarity,
            num_comparisons=len(similarities)
        )
        
        return novelty
    
    def _cosine_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """Calculate cosine similarity between two vectors"""
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        similarity = dot_product / (norm1 * norm2)
        return float(similarity)
    
    def _transform_novelty_score(self, score: float) -> float:
        """Apply non-linear transformation to novelty score for better distribution"""
        # Sigmoid-like transformation to expand middle range
        # This makes moderate novelty more distinguishable
        x = score * 2 - 1  # Scale to [-1, 1]
        transformed = 1 / (1 + np.exp(-3 * x))  # Sigmoid with steeper slope
        
        # Ensure output is in [0, 1]
        return max(0.0, min(1.0, transformed))
    
    def calculate_buzz_score(
        self,
        ticker: str,
        published_at: datetime,
        db: Session,
        window_hours: int = 24
    ) -> float:
        """
        Calculate buzz score based on document frequency for a ticker
        Returns normalized score between 0 and 1
        """
        
        # Count documents in the time window
        window_start = published_at - timedelta(hours=window_hours)
        
        doc_count = db.query(Document).filter(
            and_(
                Document.published_at >= window_start,
                Document.published_at <= published_at,
                Document.meta['tickers'].contains([ticker]) if ticker else true()
            )
        ).count()
        
        # Calculate z-score (simplified without historical mean/std)
        # Use empirical thresholds
        if doc_count <= 1:
            buzz_z = -1.0
        elif doc_count <= 3:
            buzz_z = 0.0
        elif doc_count <= 5:
            buzz_z = 0.5
        elif doc_count <= 10:
            buzz_z = 1.0
        else:
            buzz_z = 2.0
        
        # Apply sigmoid to get score in [0, 1]
        buzz_score = 1 / (1 + np.exp(-buzz_z))
        
        return buzz_score

# Global instance
novelty_calculator = NoveltyCalculator()