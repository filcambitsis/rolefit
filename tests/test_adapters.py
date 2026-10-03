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
