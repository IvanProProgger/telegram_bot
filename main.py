#!/usr/bin/env python
import asyncio
import shelve

from aiogram import Bot, Dispatcher, types

from config import HALLS, BOT_TOKEN
from loto_club import LotoClub

DB = shelve.open("database", writeback=True)

if DB.get("clients") is None:
    DB["clients"] = set()

if DB.get("hall_info") is None:
    DB["hall_info"] = {}


async def report_loop(bot: Bot) -> None:
    """Запускается каждые 3 минуты и собирает данные по залам.
    Если сумма с предыдущего прогона отличается на 100к,
    необходимо возвращать данные.
    """

    while True:
        for hall, password in HALLS.items():
            try:

                value = await LotoClub(user=hall, password=password, hall=hall).get_remains_by_clubs()
                if isinstance(value, str):
                    for client in DB["clients"]:
                        await bot.send_message(client, value, parse_mode=types.ParseMode.MARKDOWN)
                else:
                    last_value = DB["hall_info"][hall] if DB["hall_info"].get(hall) else 0
                    difference = value - last_value
                    if difference > 40_000:
                        for client in DB["clients"]:
                            msg = f"Зал {hall}: {last_value} -> {value}(+{difference})"
                            print(msg)
                            await bot.send_message(client, msg, parse_mode=types.ParseMode.MARKDOWN)
                    DB["hall_info"][hall] = value

            except Exception as exc:
                print(str(exc))
            ...

        await asyncio.sleep(3 * 60)


async def start_handler(message: types.Message) -> None:
    """Приветствие нового пользователя и добавления его в базу."""

    DB["clients"].add(message.chat.id)
    await message.answer(
        f"Привет, {message.from_user.get_mention(as_html=True)} 👋!",
        parse_mode=types.ParseMode.HTML,
    )


async def exit_handler(message: types.Message) -> None:
    """Удаление пользователя из базы."""

    if message.chat.id in DB["clients"]:
        DB["clients"].remove(message.chat.id)
        await message.answer(
            f"Пользователь, {message.from_user.get_mention(as_html=True)} успешно отписался.",
            parse_mode=types.ParseMode.HTML,
        )
    else:
        await message.answer(
            "Произошла ошибка! "
            f"Пользователь, {message.from_user.get_mention(as_html=True)} не является подписанным на события.",
            parse_mode=types.ParseMode.HTML,
        )


async def total_handler(message: types.Message) -> None:
    """Считает полную сумму из всех залов."""

    try:
        await message.answer("Идет обработка запроса...", parse_mode=types.ParseMode.MARKDOWN)

        total_value = 0
        for hall, password in HALLS.items():
            value = await LotoClub(user=hall, password=password, hall=hall).get_remains_by_clubs()
            if isinstance(value, str):
                await message.answer(value, parse_mode=types.ParseMode.MARKDOWN)
                return
            else:
                total_value += value

        total_value = '{0:,}'.format(total_value).replace(',', ' ')
        msg = f"Итого: {total_value} т"
        print(msg)
        await message.answer(msg, parse_mode=types.ParseMode.MARKDOWN)

    except:
        await message.answer(
            "Произошла ошибка при попытке получить результаты.",
            parse_mode=types.ParseMode.MARKDOWN
        )


async def halls_handler(message: types.Message) -> None:
    """Выдает сумму по каждому залу."""

    try:
        await message.answer("Идет обработка запроса...", parse_mode=types.ParseMode.MARKDOWN)

        results = []
        for hall, password in HALLS.items():
            value = await LotoClub(user=hall, password=password, hall=hall).get_remains_by_clubs(field_num=4)
            if isinstance(value, str):
                await message.answer(value, parse_mode=types.ParseMode.MARKDOWN)
                return
            else:
                value = '{0:,}'.format(value).replace(',', ' ')
                results.append(f'{hall} - {value} т\n')

        msg = ''.join(results)
        print(msg)
        await message.answer(msg, parse_mode=types.ParseMode.MARKDOWN)

    except:
        await message.answer(
            "Произошла ошибка при попытке получить результаты.",
            parse_mode=types.ParseMode.MARKDOWN
        )


async def main() -> None:
    bot = Bot(token=BOT_TOKEN)
    try:
        dispatcher = Dispatcher(bot=bot)
        dispatcher.register_message_handler(start_handler, commands={"start", "restart"})
        dispatcher.register_message_handler(exit_handler, commands={"exit"})
        dispatcher.register_message_handler(total_handler, commands={"total"})
        dispatcher.register_message_handler(halls_handler, commands={"halls"})
        asyncio.create_task(report_loop(bot))
        await dispatcher.start_polling()
    finally:
        DB.close()
        await bot.close()


if __name__ == '__main__':
    asyncio.run(main())
