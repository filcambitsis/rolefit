import asyncio
import json
from .db import SessionLocal
from .ingestion import crawl

with SessionLocal() as db:
    print(json.dumps(asyncio.run(crawl(db))))
