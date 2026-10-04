import asyncio
import httpx
import pytest
from rolefit.ingestion import fetch_board


@pytest.mark.parametrize(
    "provider,payload",
    [
        (
            "greenhouse",
            {
                "jobs": [
                    {
                        "id": 1,
                        "title": "AI Engineer",
                        "absolute_url": "https://example.com/1",
                        "content": "Hello",
                        "location": {"name": "London"},
                    }
                ]
            },
        ),
        (
            "lever",
            [
                {
                    "id": "1",
                    "text": "AI Engineer",
                    "hostedUrl": "https://example.com/1",
                    "categories": {"commitment": "Full-time", "location": "London"},
                    "description": "Hello",
                }
            ],
        ),
        (
            "ashby",
            {
                "jobs": [
                    {
                        "id": "1",
                        "title": "AI Engineer",
                        "jobUrl": "https://example.com/1",
                        "location": "London",
                        "employmentType": "FullTime",
                        "descriptionPlain": "Hello",
                        "address": None,
                    }
                ]
            },
        ),
    ],
)
def test_public_provider_shapes(provider, payload):
    async def run():
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(lambda request: httpx.Response(200, json=payload))
        ) as client:
            jobs = await fetch_board(client, {"provider": provider, "board": "test"})
            assert len(jobs) == 1 and jobs[0]["title"] == "AI Engineer"

    asyncio.run(run())


def test_invalid_board_payload_is_not_empty_success():
    async def run():
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(lambda request: httpx.Response(200, json={"error": "rate limited"}))
        ) as client:
            with pytest.raises(ValueError):
                await fetch_board(client, {"provider": "greenhouse", "board": "test"})

    asyncio.run(run())


def test_failed_crawl_preserves_old_jobs(db, job, monkeypatch, tmp_path):
    import json
    from datetime import timedelta
    from rolefit import ingestion
    from rolefit.models import now

    job.last_seen = now() - timedelta(days=10)
    db.commit()
    seeds = tmp_path / "seeds.json"
    seeds.write_text(json.dumps([{"provider": job.provider, "board": job.board, "company": job.company}]))

    async def failed(*args):
        raise ValueError("Board unavailable")

    async def no_wait(*args):
        pass

    monkeypatch.setattr(ingestion, "fetch_board", failed)
    monkeypatch.setattr(ingestion.asyncio, "sleep", no_wait)
    report = asyncio.run(ingestion.crawl(db, seeds))
    assert report["boards"][0]["error"] == "Board unavailable"
    assert job.is_open


def test_lever_european_board():
    async def run():
        def respond(request):
            assert request.url.host == "api.eu.lever.co"
            return httpx.Response(200, json=[])

        async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
            assert await fetch_board(client, {"provider": "lever", "board": "tomtom", "region": "eu"}) == []

    asyncio.run(run())


def test_foreign_duplicate_does_not_hide_dutch_job(db, job, monkeypatch, tmp_path):
    import json
    from datetime import timedelta
    from rolefit import ingestion
    from rolefit.models import Job

    foreign = Job(
        **{column.name: getattr(job, column.name) for column in Job.__table__.columns if column.name != "id"}
    )
    foreign.external_id = "foreign"
    foreign.countries = ["US"]
    foreign.first_seen = job.first_seen - timedelta(days=1)
    db.add(foreign)
    db.commit()
    seeds = tmp_path / "empty-sources.json"
    seeds.write_text(json.dumps([]))
    asyncio.run(ingestion.crawl(db, seeds))
    assert job.duplicate_of is None
