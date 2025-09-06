import spacy
from transformers import AutoTokenizer, AutoModelForSequenceClassification, pipeline
from sentence_transformers import SentenceTransformer
import torch
import numpy as np
from typing import List, Dict, Tuple, Optional
import structlog
import re

from app.core.config import settings

logger = structlog.get_logger()

class NLPPipeline:
    def __init__(self):
        self.nlp = None
        self.finbert = None
        self.embedder = None
        self._initialized = False
    
    def initialize(self):
        if self._initialized:
            return
        
        try:
            # Load spaCy model
            try:
                self.nlp = spacy.load("en_core_web_sm")
            except:
                logger.warning("spaCy model not found, downloading...")
                import subprocess
                subprocess.run(["python", "-m", "spacy", "download", "en_core_web_sm"])
                self.nlp = spacy.load("en_core_web_sm")
            
            # Load FinBERT for sentiment analysis
            logger.info("Loading FinBERT model", model=settings.FINBERT_MODEL)
            tokenizer = AutoTokenizer.from_pretrained(settings.FINBERT_MODEL)
            model = AutoModelForSequenceClassification.from_pretrained(settings.FINBERT_MODEL)
            self.finbert = pipeline("sentiment-analysis", model=model, tokenizer=tokenizer, device=-1)
            
            # Load sentence embedder
            logger.info("Loading sentence transformer", model=settings.EMBED_MODEL)
            self.embedder = SentenceTransformer(settings.EMBED_MODEL)
            
            self._initialized = True
            logger.info("NLP pipeline initialized successfully")
        except Exception as e:
            logger.error("Failed to initialize NLP pipeline", error=str(e))
            raise
    
    def extract_entities(self, text: str) -> List[Dict]:
        if not self._initialized:
            self.initialize()
        
        doc = self.nlp(text[:1000000])  # Limit text length for spaCy
        entities = []
        
        for ent in doc.ents:
            if ent.label_ in ["ORG", "PERSON", "GPE", "MONEY", "PERCENT", "DATE"]:
                entities.append({
                    "text": ent.text,
                    "type": ent.label_,
                    "start": ent.start_char,
                    "end": ent.end_char
                })
        
        return entities
    
    def extract_tickers(self, text: str, entities: List[Dict]) -> List[str]:
        # Extract potential stock tickers from text
        tickers = set()
        
        # Pattern for stock tickers (1-5 uppercase letters)
        ticker_pattern = r'\b[A-Z]{1,5}\b'
        
        # Common words to exclude
        exclude_words = {
            'I', 'A', 'THE', 'AND', 'OR', 'BUT', 'IF', 'THEN', 'CEO', 'CFO', 'CTO',
            'USA', 'US', 'UK', 'EU', 'NYSE', 'NASDAQ', 'SP', 'DJ', 'AI', 'ML',
            'API', 'HTTP', 'URL', 'HTML', 'JSON', 'XML', 'PDF', 'CSV'
        }
        
        # Look for ticker patterns in parentheses (common in financial text)
        paren_pattern = r'\(([A-Z]{1,5})\)'
        for match in re.finditer(paren_pattern, text):
            ticker = match.group(1)
            if ticker not in exclude_words:
                tickers.add(ticker)
        
        # Look for tickers after company names
        for entity in entities:
            if entity["type"] == "ORG":
                # Check text immediately after organization name
                start_pos = entity["end"]
                snippet = text[start_pos:start_pos+20]
                for match in re.finditer(ticker_pattern, snippet):
                    ticker = match.group(0)
                    if ticker not in exclude_words and len(ticker) <= 5:
                        tickers.add(ticker)
        
        # Look for common patterns like "ticker: XXXX" or "$XXXX"
        dollar_pattern = r'\$([A-Z]{1,5})\b'
        for match in re.finditer(dollar_pattern, text):
            tickers.add(match.group(1))
        
        return list(tickers)
    
    def analyze_sentiment(self, text: str) -> Tuple[str, float]:
        if not self._initialized:
            self.initialize()
        
        # Truncate text for BERT (max 512 tokens)
        truncated_text = text[:2000]
        
        try:
            results = self.finbert(truncated_text)
            if results:
                result = results[0]
                label = result['label'].lower()
                score = result['score']
                
                # Map FinBERT labels to our schema
                label_map = {
                    'positive': 'positive',
                    'negative': 'negative',
                    'neutral': 'neutral'
                }
                
                return label_map.get(label, 'neutral'), score
        except Exception as e:
            logger.warning("Sentiment analysis failed", error=str(e))
        
        return 'neutral', 0.5
    
    def generate_embedding(self, text: str) -> np.ndarray:
        if not self._initialized:
            self.initialize()
        
        # Generate embedding for text
        embedding = self.embedder.encode(text[:5000], convert_to_numpy=True)
        return embedding
    
    def process_document(self, text: str) -> Dict:
        if not self._initialized:
            self.initialize()
        
        # Extract entities
        entities = self.extract_entities(text)
        
        # Extract tickers
        tickers = self.extract_tickers(text, entities)
        
        # Analyze sentiment
        sentiment, sentiment_score = self.analyze_sentiment(text)
        
        # Generate embedding
        embedding = self.generate_embedding(text)
        
        return {
            "entities": entities,
            "tickers": tickers,
            "sentiment": sentiment,
            "sentiment_score": sentiment_score,
            "embedding": embedding.tolist()
        }

# Global instance
nlp_pipeline = NLPPipeline()