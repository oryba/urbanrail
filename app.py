import os

from urllib.parse import urljoin
from datetime import datetime
from typing import Optional, List

import pytz
from fastapi import FastAPI, Request, status, APIRouter
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from data import get_schedule, ScheduleItem, Schedule

app = FastAPI()

BASE_URL = os.getenv('BASE_URL', 'https://urbanrail.kyiv.group')

app.mount("/static", StaticFiles(directory="static"), name="static")  # regular static files
templates = Jinja2Templates(directory="templates")


@app.get("/", response_class=HTMLResponse, tags=["ssr"])
async def read_item(request: Request):
    """
    Render index page
    :param request: starlette request
    :return: static html
    """
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/stations", response_class=HTMLResponse, tags=["ssr"])
async def read_item(request: Request):
    """
    Render stations list
    :param request: starlette request
    :return: static html
    """
    schedule = await get_schedule()
    return templates.TemplateResponse("list.html", {"request": request, "schedule": schedule})


@app.get("/stations/{slug}", response_class=HTMLResponse, tags=["ssr"])
@app.get("/stations/{slug}/{day}", response_class=HTMLResponse, tags=["ssr"])
async def read_item(request: Request, slug: str, day: Optional[str] = None):
    """
    Render station schedule (by default for today, optionally - for weekend or weekday)
    :param request: starlette request
    :param slug: station slug
    :param day: None for today's schedule, 'weekday' or 'weekend' otherwise
    :return: static html
    """
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
        "request": request, "schedule": schedule, "station": station, "time": time, "day": day,
        "canonical": urljoin(BASE_URL, request.scope.get('path', ''))})


api = APIRouter()


@api.get('/schedule', tags=["rest"], response_model=Schedule)
async def api_schedule() -> Schedule:
    return Schedule(items=await get_schedule())


app.include_router(api, prefix="/v1")
app.mount("/", StaticFiles(directory="static/root"), name="root-static")

if __name__ == '__main__':
    import uvicorn

    uvicorn.run("app:app", port=5555, host="0.0.0.0")
