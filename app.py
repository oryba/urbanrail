import os

from urllib.parse import urljoin
from datetime import datetime
from typing import Optional

import pytz
from fastapi import FastAPI, Request, status, APIRouter, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.responses import RedirectResponse

from data import get_schedule, Schedule, get_trains

app = FastAPI()

BASE_URL = os.getenv('BASE_URL', 'https://urbanrail.kyiv.group')

app.mount("/static", StaticFiles(directory="static"), name="static")  # regular static files
templates = Jinja2Templates(directory="templates")

RENAME_REDIRECTS = {
    "kiyivska-rusanivka": "rusanivka",
    "kiyiv-dniprov": "mikilska-slobidka",
    "troieshchina": "voskresenka",
    "troieshchina-2": "raiduzhnyi",
    "zenit": "kurenivka",
    "vishgorodska": "priorka",
    "rubezhivska": "beresteiska",
    "kiyiv-pas-pivnichna": "vokzalna",
    "livii-bereg": "bereznyaky",
}


@app.get("/", response_class=HTMLResponse, tags=["ssr"])
async def read_item(request: Request):
    """
    Render index page
    :param request: starlette request
    :return: static html
    """
    schedule = await get_schedule()
    return templates.TemplateResponse("index.html", {"request": request, "schedule": schedule})


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
        if slug in RENAME_REDIRECTS:
            return RedirectResponse(request.url.path.replace(slug, RENAME_REDIRECTS[slug]), status_code=301)
        idx = slugs.index(slug)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    station = schedule[idx]
    now = datetime.now().astimezone(pytz.timezone('Europe/Kiev'))
    time = f"{now.hour:02d}:{now.minute:02d}"
    station['next'] = schedule[(idx + 1) % len(schedule)]
    station['prev'] = schedule[idx - 1]
    if day is None:
        detected_day = 'weekend' if now.weekday() >= 5 else 'weekday'
    else:
        detected_day = day
    if detected_day == 'weekend':
        station['departures_forth'] = [s for s in station['departures_forth'] if s['schedule'] == 'daily']
        station['departures_back'] = [s for s in station['departures_back'] if s['schedule'] == 'daily']
    return templates.TemplateResponse("station.html", {
        "request": request, "schedule": schedule, "station": station, "time": time, "day": day,
        "detected_day": detected_day, "canonical": urljoin(BASE_URL, request.scope.get('path', ''))})


@app.get("/trains/{code}", response_class=HTMLResponse, tags=["ssr"])
async def read_item(request: Request, code: str):
    """
    Render train departures by code
    :param request: starlette request
    :param code: train code
    :return: static html
    """
    code = code.replace('-', '/')
    schedule = await get_schedule()
    trains = await get_trains(schedule)
    if not trains.get(code):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    station_data = {s['slug']: s for s in schedule}
    return templates.TemplateResponse(
        "train.html", {"request": request, "st": station_data, "train": trains[code], "code": code})


api = APIRouter()


@api.get('/schedule', tags=["rest"], response_model=Schedule)
async def api_schedule() -> Schedule:
    return Schedule(items=await get_schedule())


static_files = StaticFiles(directory="static/root", html=True)


@app.exception_handler(404)
async def handle_404(request, exc):
    full_path, stat_result = await static_files.lookup_path("404.html")
    return static_files.file_response(
        full_path, stat_result, {"method": "GET", "headers": {}}, status_code=404
    )


app.include_router(api, prefix="/v1")
app.mount("/", static_files, name="root-static")

if __name__ == '__main__':
    import uvicorn

    uvicorn.run("app:app", port=5555, host="0.0.0.0")
