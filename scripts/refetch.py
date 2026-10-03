"""Re-fetch published IDs without shipping full job descriptions. Hash drift is explicit."""

import asyncio
import json
from pathlib import Path

import httpx

from rolefit.ingestion import fetch_board, normalize


async def main():
    snapshot = json.loads(Path("data/evaluation/snapshot.json").read_text())
    folder = Path("data/private/refetch")
    folder.mkdir(parents=True, exist_ok=True)
    sources = {
        (j["provider"], j["board"]): {"provider": j["provider"], "board": j["board"], "company": j["company"]}
        for j in snapshot["jobs"]
    }
    wanted = {(j["provider"], j["board"], j["external_id"]): j for j in snapshot["jobs"]}
    seen = set()
    async with httpx.AsyncClient(timeout=45, follow_redirects=True) as client:
        for source in sources.values():
            try:
                for item in await fetch_board(client, source):
                    key = (source["provider"], source["board"], item["external_id"])
                    if key not in wanted:
                        continue
                    row = normalize(source, item)
                    original = wanted[key]
                    seen.add(key)
                    if row["content_hash"] != original["content_hash"]:
                        print(
                            f"CHANGED {original['id']}: original raw text cannot be reconstructed from this posting"
                        )
                    else:
                        (folder / (original["id"] + ".txt")).write_text(row["description"])
            except httpx.HTTPError as exc:
                print(f"Board unavailable: {source['board']} ({type(exc).__name__})")
    for key in wanted.keys() - seen:
        print(f"UNAVAILABLE {wanted[key]['id']}")
    print("Evaluation uses frozen structured features and does not depend on re-fetch availability.")


if __name__ == "__main__":
    asyncio.run(main())
