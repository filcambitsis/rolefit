import asyncio
import json
from collections import Counter
from datetime import timedelta

import httpx
from sqlalchemy import select

from .config import ROOT
from .models import CrawlRun, Job, now
from .normalization import content_hash, countries, employment, family, language, strip_html, workplace


async def fetch_board(client: httpx.AsyncClient, source: dict) -> list[dict]:
    board, provider = source["board"], source["provider"]
    if provider == "greenhouse":
        response = await client.get(
            f"https://boards-api.greenhouse.io/v1/boards/{board}/jobs", params={"content": "true"}
        )
        response.raise_for_status()
        payload = response.json()
        if "jobs" not in payload or not isinstance(payload["jobs"], list):
            raise ValueError("Invalid Greenhouse payload; refusing closed detection")
        return [
            dict(
                external_id=str(j["id"]),
                title=j["title"],
                url=j["absolute_url"],
                raw=j.get("content", ""),
                location=j.get("location", {}).get("name", ""),
                employment="",
                workplace="",
                country="",
            )
            for j in payload["jobs"]
        ]
    if provider == "lever":
        jobs, skip = [], 0
        while True:
            response = await client.get(
                f"https://api.lever.co/v0/postings/{board}",
                params={"mode": "json", "limit": 100, "skip": skip},
            )
            response.raise_for_status()
            batch = response.json()
            if not isinstance(batch, list):
                raise ValueError("Invalid Lever payload; refusing closed detection")
            jobs.extend(batch)
            if len(batch) < 100:
                break
            skip += len(batch)
        return [
            dict(
                external_id=j["id"],
                title=j["text"],
                url=j["hostedUrl"],
                raw=j.get("description", "")
                + "\n"
                + "\n".join(x.get("text", "") + "\n" + x.get("content", "") for x in j.get("lists", []))
                + "\n"
                + j.get("additional", ""),
                location="; ".join(
                    j.get("categories", {}).get("allLocations", [])
                    or [j.get("categories", {}).get("location", "")]
                ),
                employment=j.get("categories", {}).get("commitment", ""),
                workplace=j.get("workplaceType", ""),
                country="",
            )
            for j in jobs
        ]
    if provider == "ashby":
        response = await client.get(f"https://api.ashbyhq.com/posting-api/job-board/{board}")
        response.raise_for_status()
        payload = response.json()
        if "jobs" not in payload or not isinstance(payload["jobs"], list):
            raise ValueError("Invalid Ashby payload; refusing closed detection")
        return [
            dict(
                external_id=j["id"],
                title=j["title"],
                url=j["jobUrl"],
                raw=j.get("descriptionHtml", j.get("descriptionPlain", "")),
                location=j.get("location", ""),
                employment=j.get("employmentType", ""),
                workplace=j.get("workplaceType", "") or ("remote" if j.get("isRemote") else ""),
                country=((j.get("address") or {}).get("postalAddress") or {}).get("addressCountry", ""),
            )
            for j in payload["jobs"]
            if j.get("isListed", True)
        ]
    raise ValueError(f"Unsupported provider {provider}")


def normalize(source: dict, item: dict) -> dict:
    text = strip_html(item["raw"])
    emp, emp_source = employment(item["employment"], item["title"] + "\n" + text)
    place, place_source = workplace(item["workplace"], item["location"], text)
    return dict(
        provider=source["provider"],
        board=source["board"],
        company=source["company"],
        external_id=item["external_id"],
        title=item["title"],
        url=item["url"],
        description=text,
        content_hash=content_hash(item["title"] + "\n" + text),
        location=item["location"],
        countries=countries(item["location"], item["country"]),
        family=family(item["title"]),
        language=language(text),
        employment=emp,
        employment_provenance=emp_source,
        workplace=place,
        workplace_provenance=place_source,
    )


def reconcile(db, source: dict, records: list[dict], timestamp):
    existing = {
        j.external_id: j
        for j in db.scalars(
            select(Job).where(Job.provider == source["provider"], Job.board == source["board"])
        )
    }
    stats = Counter()
    seen = set()
    for row in records:
        seen.add(row["external_id"])
        job = existing.get(row["external_id"])
        if job:
            changed = job.content_hash != row["content_hash"]
            if changed:
                from sqlalchemy import delete
                from .models import Requirement

                db.execute(delete(Requirement).where(Requirement.job_id == job.id))
                job.embedding = None
                stats["updated"] += 1
            for key, value in row.items():
                setattr(job, key, value)
        else:
            job = Job(**row)
            db.add(job)
            stats["added"] += 1
        job.is_open, job.last_seen = True, timestamp
        db.flush()
    # Only a successful full board response can close jobs; empty responses use a grace period.
    for external_id, job in existing.items():
        last_seen = job.last_seen.replace(tzinfo=timestamp.tzinfo)
        if external_id not in seen and job.is_open and timestamp - last_seen >= timedelta(hours=24):
            job.is_open = False
            stats["closed"] += 1
    return dict(stats)


async def crawl(db, seeds_path=None):
    sources = json.loads((seeds_path or ROOT / "data/seeds.json").read_text())
    run = CrawlRun(report={})
    db.add(run)
    db.commit()
    semaphore = asyncio.Semaphore(4)
    async with httpx.AsyncClient(
        timeout=45, follow_redirects=True, headers={"User-Agent": "RoleFit/0.1 (public job research)"}
    ) as client:

        async def get(source):
            async with semaphore:
                for attempt in range(3):
                    try:
                        return source, await fetch_board(client, source), None
                    except (httpx.HTTPError, ValueError, KeyError, TypeError, AttributeError) as exc:
                        if attempt == 2:
                            return source, [], str(exc)[:250]
                        await asyncio.sleep(2**attempt)

        batches = await asyncio.gather(*(get(s) for s in sources))
    report = {"boards": [], "providers": {}, "families": {}, "eligible": 0}
    for source, items, error in batches:
        if error:
            report["boards"].append({**source, "error": error})
            continue
        records = [normalize(source, item) for item in items]
        counts = reconcile(db, source, records, now())
        db.commit()
        report["boards"].append({**source, "fetched": len(records), **counts})
    # Recompute canonical copies from OPEN jobs: an old closed duplicate must not hide an open one.
    hashes = {}
    jobs = list(db.scalars(select(Job).order_by(Job.first_seen, Job.id)))
    for job in jobs:
        job.duplicate_of = None
        if job.is_open:
            if job.content_hash in hashes:
                job.duplicate_of = hashes[job.content_hash]
            else:
                hashes[job.content_hash] = job.id
    eligible = [
        j
        for j in jobs
        if j.is_open
        and not j.duplicate_of
        and j.family
        and j.language == "en"
        and j.employment in ("full-time", "part-time", "internship")
    ]
    report.update(
        eligible=len(eligible),
        providers=dict(Counter(j.provider for j in eligible)),
        families=dict(Counter(j.family for j in eligible)),
        total=len(jobs),
    )
    report["corpus_gate_passed"] = len(eligible) >= 200
    report["consultant_decision"] = "review yield and annotation accuracy before locking family"
    run.report, run.finished_at = report, now()
    db.commit()
    return report
