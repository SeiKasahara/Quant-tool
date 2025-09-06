import argparse
import yaml
import asyncio
from app.configs import sources as sources_cfg
from app.adapters.news_rss import NewsRSSAdapter
from app.ingestion.pipeline import save_document_from_raw
import structlog

logger = structlog.get_logger()

def load_sources(path='app/configs/sources.yaml'):
    with open(path, 'r', encoding='utf8') as f:
        return yaml.safe_load(f)

async def run_once(source_name: str):
    cfg = load_sources()
    for s in cfg.get('sources', []):
        if s.get('name') == source_name:
            adapter = None
            if s.get('type') == 'news':
                adapter = NewsRSSAdapter(s)
            else:
                logger.warning('unsupported_source_type', type=s.get('type'))
                return

            docs = await adapter.fetch()
            for raw in docs:
                save_document_from_raw(raw.__dict__ if hasattr(raw, '__dict__') else raw)
            return

    logger.error('source_not_found', source=source_name)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--run-once', action='store_true')
    parser.add_argument('--source')
    args = parser.parse_args()

    if args.run_once and args.source:
        asyncio.run(run_once(args.source))
    else:
        print('Usage: --run-once --source <source_name>')

if __name__ == '__main__':
    main()
