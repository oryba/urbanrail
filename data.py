import asyncio
import json
import os
from datetime import datetime
from typing import List, Dict
from collections import defaultdict

import httpx
from bs4 import BeautifulSoup
from slugify import slugify
from pydantic import BaseModel

URLS_SCHEDULE = [
    "https://swrailway.gov.ua/timetable/eltrain/?gid=1&rid=471",
    "https://swrailway.gov.ua/timetable/eltrain/?gid=1&rid=480",
]

REMOVE_TRAINS_WEEKDAY = {
    "darnitsia": {
        "departures_forth": {
            "schedule": "weekday"
        }
    },
    **{
        slug: {
            "departures_forth": {
                "schedule": "weekday"
            },
            "departures_back": {
                "schedule": "weekday"
            }
        } for slug in [
            "rusanivka", "livoberezhna", "mikilska-slobidka", "voskresenka", "raiduzhnyi", "pochaina",
            "kurenivka", "priorka", "sirets", "beresteiska"
        ]
    },
    "sviatoshin": {
        "departures_back": {
            "schedule": "weekday"
        }
    }
}

REMOVE_TRAINS_WEEKEND = {}
# {
#     "mikilska-slobidka": {
#         "departures_forth": {}
#     },
#     **{
#         slug: {
#             "departures_forth": {},
#             "departures_back": {}
#         } for slug in ["voskresenka", "raiduzhnyi"]
#     },
#     "pochaina": {
#         "departures_back": {}
#     }
# }


class Departure(BaseModel):
    schedule: str
    code: str
    time: str


class ScheduleItem(BaseModel):
    station: str
    slug: str
    departures_forth: List[Departure]
    departures_back: List[Departure]
    transfers: List[str]
    transfer_details: Dict[str, List[str]]


class Schedule(BaseModel):
    items: List[ScheduleItem]


def sort_departures(els: list) -> List:
    return list(sorted(
        [dict(t) for t in {tuple(d.items()) for d in els}],
        key=lambda x: x['time'])
    )


def parse_tables(soup, station_names, idx):
    station_names = station_names[:]
    table = soup.find(id=idx).find(class_="gotime")
    trains = []
    for item in table.find_all(class_="on_right_t"):
        ctx = item.find(class_="et").text
        trains.append({
            'schedule': 'daily' if 'щоденно' in ctx.lower() else 'weekday',
            'code': ctx.split(',')[0].strip()
        })

    stations = {}

    for row in table.find('tbody').find_all('tr'):
        if 'on' in row.attrs.get('class', []) or 'onx' in row.attrs.get('class', []):
            cells = row.find_all(class_='q1') or row.find_all(class_='q0')
            if not cells:
                continue
            station = station_names.pop(0)
            deps = []
            _trains = trains[:]
            for i, cell in enumerate(cells):
                if not i % 2:
                    continue
                train = _trains.pop(0)
                if cell.text.strip() == '–':
                    continue
                deps.append({**train, "time": cell.text})
            if station not in stations:
                stations[station] = deps
            else:
                stations[station] = sort_departures(stations[station] + deps)
    return stations


TRANSFERS = {
    'livoberezhna': {'Лівобережна': ['m1']},
    'troieshchina-2': {'Троєщина-2': ['t4', 't5']},
    'pochaina': {'Почайна': ['m2']},
    'sirets': {'Сирець': ['m3']},
    'rubezhivska': {'Берестейська': ['m1']},
    'borshchagivka': {'Сімʼї Сосніних': ['t1', 't3']},
    'sviatoshin': {'Святошин': ['m1']},
    'kiyiv-pas-pivnichna': {'Вокзальна': ['m1'], 'Старовокзальна': ['t1', 't3']},
    'vidubichi': {'Видубичі': ['m3']}
}

TRANSFERS_BADGES = {k: sum([i for i in v.values()], []) for k, v in TRANSFERS.items()}


def cache(seconds=3600, name='schedule.json'):
    def wrap(func):
        async def _cached(*args, **kwargs):
            data = None
            try:
                with open(name, "r") as f:
                    data = json.load(f)
                upd_time = datetime.fromisoformat(
                    data['upd_time']
                ) if isinstance(data, dict) and 'upd_time' in data else None
                if (upd_time and (datetime.now() - upd_time).total_seconds() < seconds) \
                        or os.getenv("AUTO_UPDATE") != "true":
                    # return cached data
                    return data['content']
            except Exception as e:
                print("Caching error: ", e)

            try:
                res = await func(*args, **kwargs)
            except Exception as e:
                print("Error getting the actual schedule: ", e)
                if data:
                    return data['content']
                else:
                    raise e

            with open(name, "w") as f:
                json.dump({
                    'content': res,
                    'upd_time': datetime.now().isoformat()
                }, f, indent=4)

            print(f"Cache for {name} updated successfully")
            return res

        return _cached

    return wrap


def process_station_names(tab: BeautifulSoup) -> List[str]:
    return [
        el.text.strip().strip('\n').replace('з.п. ', '')
        for el in tab.find(class_="left").find_all(class_="et")
    ]


async def get_schedule_by_url(url: str) -> List[dict]:
    async with httpx.AsyncClient() as client:
        resp = await client.get(url, timeout=5)

    soup = BeautifulSoup(resp.content, features="html5lib")
    schedule = []

    # get station names on both directions
    station_names_forth = process_station_names(
        soup.find(id="tabs-trains1")
    )
    station_names_back = process_station_names(
        soup.find(id="tabs-trains2")
    )

    # get schedule for each station
    stations_forth = parse_tables(soup, station_names_forth, "tabs-trains1")
    stations_back = parse_tables(soup, station_names_back, "tabs-trains2")
    for station in stations_forth:
        if not stations_forth[station]:
            continue  # skipping stations with no departures
        schedule.append({
            'station': station,
            'slug': slugify(station),
            'departures_forth': stations_forth[station],
            'departures_back': stations_back[station]
        })

    return schedule


def merge_schedules(schedules: list) -> List[dict]:
    """
    Get departure dates from all listed schedules. Assumes that the first item contains all needed stations
    :param schedules: list of schedules
    :return: aggregated schedule
    """
    res = []
    for sch in schedules:
        for st in sch:
            existing_sts = [el for el in res if el['slug'] == st['slug']]
            if not existing_sts:
                res.append(st)
            else:
                for key in ('departures_forth', 'departures_back'):
                    existing_sts[0][key] = sort_departures(existing_sts[0][key] + st[key])

    return res


@cache(seconds=86400)
async def _get_base_schedule() -> List[dict]:
    """
    Get schedule for every station in both directions
    :return: list of stations with additional properties
    """

    # Livii Bereg station is totally insane in UZ schedule, this allows to mock some departures
    mocked_sch = [
        {
            'station': 'Лівий Берег', 'slug': 'livii-bereg', 'departures_forth': [],
            'departures_back': [
                {'schedule': 'daily', 'code': '7301', 'time': '05:43'},
                {'schedule': 'daily', 'code': '7302/7303', 'time': '06:43'},
                {'schedule': 'weekday', 'code': '7305', 'time': '07:13'},
                {'schedule': 'daily', 'code': '7306/7307', 'time': '07:43'},
                {'schedule': 'weekday', 'code': '7308/7309', 'time': '08:13'},
                {'schedule': 'daily', 'code': '7310/7311', 'time': '08:43'},
                {'schedule': 'weekday', 'code': '7312/7313', 'time': '09:13'},
                {'schedule': 'daily', 'code': '7314/7315', 'time': '09:43'},
                {'schedule': 'weekday', 'code': '7316/7317', 'time': '10:13'},
                {'schedule': 'daily', 'code': '7318/7319', 'time': '10:43'},
                {'schedule': 'daily', 'code': '7320/7321', 'time': '11:43'},
                {'schedule': 'daily', 'code': '7322/7323', 'time': '12:43'},
                {'schedule': 'daily', 'code': '7324/7325', 'time': '13:43'},
                {'schedule': 'daily', 'code': '7326/7327', 'time': '14:43'},
                {'schedule': 'daily', 'code': '7328/7329', 'time': '15:43'},
                {'schedule': 'daily', 'code': '7330/7331', 'time': '16:43'},
                {'schedule': 'weekday', 'code': '7332/7333', 'time': '17:13'},
                {'schedule': 'daily', 'code': '7334/7335', 'time': '17:43'},
                {'schedule': 'weekday', 'code': '7336/7337', 'time': '18:13'},
                {'schedule': 'daily', 'code': '7338/7339', 'time': '18:43'},
                {'schedule': 'weekday', 'code': '7340/7341', 'time': '19:13'},
                {'schedule': 'daily', 'code': '7342/7343', 'time': '19:43'},
                {'schedule': 'daily', 'code': '7344/7345', 'time': '20:43'},
                {'schedule': 'daily', 'code': '7346/7347', 'time': '21:43'},
                {'schedule': 'daily', 'code': '7348/7349', 'time': '22:43'},
            ],
            'transfers': [], 'transfer_details': []
        }
    ]

    schedules = [
        await get_schedule_by_url(url) for url in URLS_SCHEDULE
    ] + [mocked_sch]

    schedule = merge_schedules(schedules)

    # Get transfer optinos
    for station in schedule:
        station['transfers'] = TRANSFERS_BADGES.get(station['slug'], [])
        station['transfer_details'] = TRANSFERS.get(station['slug'], [])

    return schedule


async def get_schedule() -> List[dict]:
    """
    Get schedule with warnings and temporary changes
    :return: list of stations with additional properties
    """
    schedule = await _get_base_schedule()

    for station in schedule:
        station["station_seo"] = station["station"] if not station.get("old_name") \
            else f'{station["station"]} (раніше: {station["old_name"]})'

        rm_wd = REMOVE_TRAINS_WEEKDAY.get(station["slug"], {})
        rm_we = REMOVE_TRAINS_WEEKEND.get(station["slug"], {})

        for key, props in rm_wd.items():
            for item in station[key]:
                if props and not all(item[k] == v for k, v in props.items()):
                    continue
                item["removed"] = {"when": ["weekday"]}

        for key, props in rm_we.items():
            for item in station[key]:
                if props and not all(item[k] == v for k, v in props.items()):
                    continue
                if item.get("removed") is not None:
                    item["removed"]["when"].append("weekend")
                else:
                    item["removed"] = {"when": ["weekend"]}

    return schedule


def generate_departures(station):
    for train in station['departures_forth']:
        yield train, 'forth'
    for train in station['departures_back']:
        yield train, 'back'


def dep_to_min(dep_time: str):
    hours, minutes = dep_time.split(':')
    return int(hours) * 60 + int(minutes)


def pluralize_int(i: int, singular, plu1, plu2) -> str:
    s = str(i)
    if len(s) >= 2 and s[-2] == '1':
        return s + " " + plu2
    elif s[-1] == '1':
        return s + " " + singular
    elif s[-1] in ['0', '2', '3', '4']:
        return s + " " + plu1
    return s + " " + plu2


@cache(seconds=86400, name='trains.json')
async def get_trains(schedule: List[Dict]) -> Dict:
    trains = defaultdict(lambda: {'schedule': '', 'direction': '', 'departures': []})
    for station in schedule:
        for train, direction in generate_departures(station):
            obj = trains[train['code']]
            obj['schedule'] = train['schedule']
            obj['direction'] = direction
            obj['departures'].append(
                (station['slug'], train['time'])
            )
    for train, td in trains.items():
        deps = list(sorted(td['departures'], key=lambda x: x[1]))  # sort by departure date
        intervals = [
            pluralize_int(
                dep_to_min(b[1]) - dep_to_min(a[1]),
                "хвилина",
                "хвилини",
                "хвилин"
            )
            for a, b in zip(deps, deps[1:])
        ]
        # TODO: make Jinja2 filter
        td['departures'] = [(el[0], el[1], diff) for el, diff in list(zip(deps, [""] + intervals))]
    return trains


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(get_schedule())
