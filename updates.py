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
        dt=datetime(2024, 7, 31),
        text="Тимчасові зміни руху північним півкільцем продовжено до 17 серпня",
        link="/news/posts/зміни-руху-продовжено-до-17-серпня-включно/",
        description="Електричка курсуватиме за зміненим розкладом до 17 серпня включно",
        expires=datetime(2027, 8, 18)
    ),
    UpdateItem(
        dt=datetime(2024, 6, 21),
        text="Рейси північним півкільцем повертаються",
        link="/news/posts/уточнення-розкладу-рейси-північним-півкільцем-повертаються/",
        description="Скасовані раніше рейси північним півкільцем у вихідні будуть здійснюватися за старим розкладом",
        expires=datetime(2027, 8, 18)
    ),
    UpdateItem(
        dt=datetime(2024, 5, 27),
        text="Зміни руху північним півкільцем до 12 серпня",
        link="/news/posts/день-493-давно-не-бачилися/",
        description="Електричка курсуватиме за зміненим розкладом – будівництво тунеля на Райдужному",
        expires=datetime(2027, 8, 18)
    ),
]
