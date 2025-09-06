# Signal Detection System - Public Info → NLP → Signal Alert MVP

An end-to-end financial signal detection system that processes public news feeds, applies NLP analysis, generates trading signals with confidence scores, and provides a web interface for monitoring and analysis.

## Features

- **Automated Data Ingestion**: RSS feed processing with content extraction
- **NLP Pipeline**: Entity recognition, sentiment analysis, event extraction, novelty detection
- **Signal Generation**: Multi-factor confidence scoring with time decay
- **Web Interface**: Real-time signal monitoring with detailed evidence
- **Slack Alerts**: Configurable notifications for high-confidence signals
- **Event Study Backtesting**: Statistical analysis of signal performance

## Architecture

```
News Feeds → Ingestion → NLP Processing → Event Extraction → Signal Fusion → Database
                                                                    ↓
                                                        REST API ← Frontend (Next.js)
                                                            ↓
                                                        Slack Alerts
```

## Quick Start

### Prerequisites

- Docker and Docker Compose
- 8GB+ RAM recommended
- Ports 3000, 5432, 6379, 8000 available

### Installation

1. Clone the repository and navigate to the project directory

2. Copy environment configuration:
```bash
cp .env.example .env
```

3. Start all services:
```bash
docker-compose up --build -d
```

4. Initialize database (first time only):
```bash
docker compose exec api alembic upgrade head
```

5. Trigger initial data ingestion:
```bash
docker compose exec api python -m app.flows.ingest --once
```

6. Access the web interface:
- Frontend: http://localhost:3000/signals
- API Documentation: http://localhost:8000/docs

## Environment Variables

Key configuration in `.env`:

- `SLACK_WEBHOOK`: Slack incoming webhook URL (optional)
- `FINBERT_MODEL`: FinBERT model for sentiment analysis
- `EMBED_MODEL`: Sentence transformer model for embeddings
- `NEWS_FEEDS`: Comma-separated RSS feed URLs
- Confidence weights: `W_SRC`, `W_NOVEL`, `W_EVT`, `W_BUZZ`

## API Endpoints

### Core Endpoints

- `GET /health` - System health check
- `GET /signals?min_confidence=0.6` - List signals with filters
- `GET /documents/{id}` - Document details with entities and events
- `GET /tickers/{symbol}/signals` - Signals for specific ticker
- `POST /backtest/event-study` - Run event study analysis

### Example API Calls

```bash
# Get recent signals
curl http://localhost:8000/signals?min_confidence=0.7

# Get document details
curl http://localhost:8000/documents/1

# Get ticker signals
curl http://localhost:8000/tickers/AAPL/signals

# Run backtest
curl -X POST http://localhost:8000/backtest/event-study \
  -H "Content-Type: application/json" \
  -d '{"event_types": ["guidance_up"], "window_days": 5}'
```

## Frontend Pages

### /signals
Main dashboard with signal list, filters, and evidence drawer
![Signals Page](docs/signals-page.png)

### /documents/{id}
Document viewer with extracted entities, events, and price chart
![Document Page](docs/document-page.png)

### /tickers/{symbol}
Ticker-specific signals with price chart and signal markers

## Confidence Scoring

The system uses a multi-factor approach:

```
confidence = calibrator(
  base_score * time_decay + adjustments
)

where:
- base_score = weighted sum of source, novelty, event, buzz
- adjustments = consistency and uncertainty factors
- time_decay = exponential decay over time
```

## Data Flow

1. **Ingestion**: Fetches RSS feeds or uses mock data
2. **Content Extraction**: Uses trafilatura for text extraction
3. **NLP Processing**:
   - Named Entity Recognition (spaCy)
   - Sentiment Analysis (FinBERT)
   - Embeddings (Sentence Transformers)
4. **Event Detection**: Rule-based pattern matching
5. **Novelty Calculation**: Cosine similarity with recent documents
6. **Signal Generation**: Confidence scoring and fusion
7. **Notifications**: Slack alerts for high-confidence signals

## Development

### Running Tests
```bash
docker compose exec api pytest
```

### Manual Ingestion
```bash
docker compose exec api python -m app.flows.ingest --once --mock
```

### View Logs
```bash
docker compose logs -f api
docker compose logs -f web
```

### Database Access
```bash
docker compose exec db psql -U user -d signals
```

## Mock Data

The system includes mock articles for testing:
- Apple guidance raise
- Tesla earnings beat
- Microsoft acquisition
- Amazon regulatory probe
- NVIDIA dividend increase

Mock data is automatically used when:
- RSS feeds are unavailable
- Running with `--mock` flag
- API endpoints fail

## Monitoring

- Health endpoint: http://localhost:8000/health
- Structured JSON logs in all services
- Audit trail for all critical operations
- Signal evidence tracking

## Compliance

- Only processes public information sources
- Stores document snapshots for audit
- Flags signals requiring second source confirmation
- Full audit logging of signal generation

## Troubleshooting

### Services not starting
```bash
docker compose down
docker compose up --build
```

### Database connection errors
```bash
docker compose restart db
docker compose exec api alembic upgrade head
```

### No signals appearing
```bash
# Check ingestion logs
docker compose logs api | grep "ingest"

# Run manual ingestion with mock data
docker compose exec api python -m app.flows.ingest --once --mock
```

## Architecture Details

### Technology Stack
- **Backend**: Python 3.11, FastAPI, SQLAlchemy, Prefect
- **NLP**: spaCy, Transformers, Sentence-Transformers
- **Database**: PostgreSQL 15 with pgvector extension
- **Cache**: Redis
- **Frontend**: Next.js 14, TypeScript, TailwindCSS, Recharts
- **Notifications**: Slack Webhooks

### Database Schema
- Companies & Tickers
- Documents with embeddings
- Entities & Events
- Signals with evidence
- Audit logs

## License

MIT