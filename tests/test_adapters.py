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


def test_workable_locations_and_employment():
    from rolefit.ingestion import normalize

    payload = {
        "jobs": [
            {
                "shortcode": "ABC",
                "title": "Data Analyst",
                "url": "https://example.com/job",
                "description": "Required: Python and SQL. Build reporting dashboards for our team.",
                "employment_type": "Full-time",
                "workplace_type": "hybrid",
                "locations": [
                    {"city": "Athens", "country": "Greece"},
                    {"city": "Amsterdam", "country": "Netherlands"},
                ],
            }
        ]
    }

    payload["jobs"].append({**payload["jobs"][0], "locations": [{"city": "Berlin", "country": "Germany"}]})

    async def run():
        def respond(request):
            assert request.url.params["details"] == "true"
            return httpx.Response(200, json=payload)

        async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
            source = {"provider": "workable", "board": "test", "company": "Test"}
            records = await fetch_board(client, source)
            assert len(records) == 1
            job = normalize(source, records[0])
            assert set(job["countries"]) == {"GR", "NL", "DE"}
            assert job["employment"] == "full-time"
            assert job["workplace"] == "hybrid"
            assert job["description"].startswith("Required:")

    asyncio.run(run())


@pytest.mark.parametrize("payload", [{"error": "unavailable"}, {"jobs": None}, []])
def test_workable_invalid_feed_does_not_close_jobs(payload):
    async def run():
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(lambda request: httpx.Response(200, json=payload))
        ) as client:
            with pytest.raises(ValueError):
                await fetch_board(client, {"provider": "workable", "board": "test"})

    asyncio.run(run())
