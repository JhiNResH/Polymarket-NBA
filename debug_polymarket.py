import asyncio
import httpx
from datetime import datetime
import json

async def main():
    url = "https://gamma-api.polymarket.com/events"
    params = {
        # "series_id": "10345",  # REMOVED
        "closed": "false",
        "order": "startTime",
        "ascending": "true",
        "limit": 1000  # Deep search
    }
    
    print(f"Fetching from {url}...")
    async with httpx.AsyncClient() as client:
        resp = await client.get(url, params=params)
        events = resp.json()
        
    print(f"Found {len(events)} events")
    
    dates = []
    found_16 = False
    
    for e in events:
        title = e.get("title")
        start = e.get("startDate")
        if not start: continue
        
        # Parse
        dt = datetime.fromisoformat(start.replace("Z", "+00:00"))
        date_str = str(dt.date())
        dates.append(date_str)
        
        # Filter locally for NBA
        if "NBA" not in title and "Basketball" not in title and "Celtics" not in title and "Lakers" not in title:
             # Basic keyword filter
             continue

        dates.append(date_str)
        
        if "Knicks" in title or "Warriors" in title or "Cavaliers" in title:
             print(f"  > POTENTIAL MATCH: {title} at {start} (Series: {e.get('seriesId')})")
             
        dates.append(date_str)
        
        if "2026-01-16" in date_str or "2026-01-17" in date_str:
            print(f"MATCH FOUND: {title}")
            print(f"  - Start: {start}")
            print(f"  - Series ID: {e.get('seriesId')}")
            print(f"  - Tag IDs: {e.get('tags')}")
            found_16 = True
            
    dates = sorted(list(set(dates)))
    print(f"\nUnique Dates found: {dates}")
    
    if not found_16:
        print("\n❌ No events found for 2026-01-16")

if __name__ == "__main__":
    asyncio.run(main())
