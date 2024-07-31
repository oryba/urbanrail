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
    link: Optional[str] = None

    def __post_init__(self):
        self.dt_local = f"{self.dt.day} {MONTHS_GEN[self.dt.month]} {self.dt.year}"
        self.dt_local_month = f"{self.dt.day} {MONTHS_GEN[self.dt.month]}"


UPDATES = [
    UpdateItem(
        dt=datetime(2024, 7, 31),
        text="Тимчасові зміни руху північним півкільцем продовжено до 17 серпня",
        link="/news/posts/зміни-руху-продовжено-до-17-серпня-включно/"
    ),
    UpdateItem(
        dt=datetime(2024, 6, 21),
        text="Рейси північним півкільцем повертаються",
        link="/news/posts/уточнення-розкладу-рейси-північним-півкільцем-повертаються/"
    ),
    UpdateItem(
        dt=datetime(2024, 5, 27),
        text="Зміни руху північним півкільцем до 12 серпня",
        link="/news/posts/день-493-давно-не-бачилися/"
    ),
]
