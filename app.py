from datetime import datetime
from typing import Optional

import pytz
from fastapi import FastAPI, Request, status
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from data import get_schedule

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


@app.get("/", response_class=HTMLResponse)
async def read_item(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/stations", response_class=HTMLResponse)
async def read_item(request: Request):
    schedule = await get_schedule()
    return templates.TemplateResponse("list.html", {"request": request, "schedule": schedule})


@app.get("/stations/{slug}", response_class=HTMLResponse)
@app.get("/stations/{slug}/{day}", response_class=HTMLResponse)
async def read_item(request: Request, slug: str, day: Optional[str] = None):
    schedule = await get_schedule()
    slugs = [s['slug'] for s in schedule]
    try:
        idx = slugs.index(slug)
    except ValueError:
        raise status.HTTP_404_NOT_FOUND
    station = schedule[idx]
    now = datetime.now().astimezone(pytz.timezone('Europe/Kiev'))
    time = f"{now.hour:02d}:{now.minute:02d}"
    station['next'] = schedule[(idx + 1) % len(schedule)]
    station['prev'] = schedule[idx - 1]
    if day == 'weekend' or (day is None and now.weekday() >= 5):
        station['departures_forth'] = [s for s in station['departures_forth'] if s['schedule'] == 'daily']
        station['departures_back'] = [s for s in station['departures_back'] if s['schedule'] == 'daily']
    return templates.TemplateResponse("station.html", {
        "request": request, "schedule": schedule, "station": station, "time": time, "day": day})


app.mount("/", StaticFiles(directory="static/root"), name="root-static")

if __name__ == '__main__':
    import uvicorn

    uvicorn.run("app:app", port=5555, host="0.0.0.0")
