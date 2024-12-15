from dataclasses import dataclass
from datetime import datetime
from typing import Optional

# as an alternative it's possible to set up uk-UA locale in Docker, but this solution is way more simple for the purpose
MONTHS_GEN = {
    1: "січня",
    2: "лютого",
    3: "березня",
    4: "квітня",
    5: "травня",
    6: "червня",
    7: "липня",
    8: "серпня",
    9: "вересня",
    10: "жовтня",
    11: "листопада",
    12: "грудня"
}


@dataclass
class UpdateItem:
    dt: datetime
    text: str
    expires: Optional[datetime] = None
    link: Optional[str] = None
    description: Optional[str] = "Оновлено розклад міської електрички"

    def __post_init__(self):
        self.dt_local = f"{self.dt.day} {MONTHS_GEN[self.dt.month]} {self.dt.year}"
        self.dt_local_month = f"{self.dt.day} {MONTHS_GEN[self.dt.month]}"


UPDATES = [
    UpdateItem(
        dt=datetime(2024, 12, 11),
        text="З 15 грудня повертаються усі рейси північним півкільцем",
        link="/news/posts/з-15-грудня-повертаються-усі-рейси-північним-півкільцем/",
        description="Повертаються щопівгодинні рейси північним півкільцем та найпізніший рейс із Дарниці через Почайну",
        expires=datetime(2027, 8, 18)
    ),
    UpdateItem(
        dt=datetime(2024, 12, 11),
        text="12 грудня станція Святошин не працюватиме з 9:00 до 17:00",
        link="/news/posts/12-грудня-станція-святошин-не-працюватиме-з-900-до-1700/",
        description="Поїзди прямуватимуть від Берестейської одразу до Борщагівської та навпаки",
        expires=datetime(2024, 12, 13)
    ),
    UpdateItem(
        dt=datetime(2024, 7, 31),
        text="Тимчасові зміни руху північним півкільцем продовжено до закінчення робіт",
        link="/news/posts/зміни-руху-північним-півкільцем-київської-міської-електрички-продовжено/",
        description="Зміни розкладу міської електрички діятимуть ще певний час",
        expires=datetime(2024, 12, 15)
    ),
]
