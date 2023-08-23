# !/usr/bin/env python
from datetime import datetime
from typing import Final, Any

import aiohttp
from bs4 import BeautifulSoup
from random_user_agent.user_agent import UserAgent

from config import MONTHS


class LotoClub:
    URL: Final[str] = "https://lk.lotoclub.kz"
    AGENT: Final[str] = UserAgent().get_random_user_agent()
    BOUNDARY: Final[str] = "----WebKitFormBoundarywmNhbYWVF3ibADkE"

    def __init__(self, user: str, password: str, hall: str | None):
        self.user = user
        self.password = password
        self.hall = hall or user

    async def get_remains_by_clubs(self, field_num: int = 0) -> float | str:
        """Основная функция запроса на сайт и сбору суммы по каждому передаваемому залу."""

        empty: str = "<strong>Записей не найдено</strong>"

        async with aiohttp.ClientSession(
                headers=self._headers(),
                cookie_jar=aiohttp.CookieJar(unsafe=True)
        ) as session:
            login_payload = {
                "username": self.user,
                "password": self.password
            }
            async with session.post(f"{self.URL}/api/mobile/v1/login", data=login_payload) as response:
                if not response.ok:
                    return f"Error: HTTP {response.status}\nHall №{self.hall}"
                token = (await response.json())["cookie"]
                session.cookie_jar.update_cookies({"bbp-cookie": token})

            with aiohttp.MultipartWriter('form-data', self.BOUNDARY) as writer:
                writer.headers["Content-Type"] = f"multipart/form-data; boundary={self.BOUNDARY}"
                for key, value in self._data_payload().items():
                    part = writer.append(value, {'Content-Type': 'form-data'})
                    part.set_content_disposition('form-data', quote_fields=False, name=key)

                async with session.post(f"{self.URL}/kz/{self.hall}/cashbox", data=writer) as resp:
                    data = await resp.text()
                    if empty in data:
                        return 0.0
                    soup = BeautifulSoup(data, 'html.parser')
                    _, soup = soup.find_all("tr", {"class": "info"})
                    soup = soup.find_all("td", {"class": "money"})
                    return float(soup[field_num].string)

    def _headers(self) -> dict[str, Any]:
        return {
            "User-Agent": self.AGENT,
            "Host": "lk.lotoclub.kz",
            "X-PJAX": "true",
            "X-Requested-With": "XMLHttpRequest",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
        }

    def _data_payload(self) -> dict[str, Any]:
        date = datetime.now()
        now = date.strftime("%d.%m.%Y")
        return {
            "period[group_by]": "day",
            "period[dt_begin]": now,
            "period[dt_finish]": now,
            "period[m_begin]": f"{MONTHS[date.month]} {date.year}",
            "period[m_finish]": f"{MONTHS[date.month]} {date.year}",
            "period[mn_y_begin]": f"{MONTHS[date.month]} {date.year - 1}",
            "period[mn_y_finish]": f"{MONTHS[date.month]} {date.year}",
            # "period[time_begin]": "00:00:00",
            # "period[time_finish]": "00:00:00",
            "period[time_shift]": "6",
            f"period[halls][{self.hall}]": self.hall,
            "period[shift]": "on",
            "period[cash_money]": "1",
            "period[non_cash_money]": "1",
            "period[ukm_non_cash_money]": "1",
        }
