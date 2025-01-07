# -*- coding: utf-8 -*-
"""
Объединённая библиотека для перевода через скрытый RPC Google Translate.

- Умеет искать массив с вариантами перевода (как второй вариант).
- Умеет склеивать несколько частей предложений (как первый вариант).
- При получении нескольких переводов одного слова берёт первый (п. 2.1).
- Если есть несколько частей одного перевода, склеивает их (п. 2.2).

Copyright (c) 2022-2025
Permission is hereby granted, free of charge, to any person obtaining a copy of this software
...
"""
import asyncio
import json
import random
import typing
import os

import httpx

from aiogtrans import urls
from aiogtrans.constants import (
    DEFAULT_CLIENT_SERVICE_URLS,
    DEFAULT_FALLBACK_SERVICE_URLS,
    DEFAULT_RAISE_EXCEPTION,
    DEFAULT_USER_AGENT,
    LANGCODES,
    LANGUAGES,
    SPECIAL_CASES,
)
from aiogtrans.models import Detected, Translated, TranslatedPart

RPC_ID = "MkEWBc"


class Translator:
    """
    Объединённая версия Google Translate Ajax API Translator

    Создайте экземпляр этого класса для доступа к «скрытому» RPC-интерфейсу Google Translate.
    """

    def __init__(
        self,
        loop: asyncio.AbstractEventLoop = asyncio.new_event_loop(),
        _aclient: httpx.AsyncClient = None,
        service_urls: typing.Union[list, tuple] = DEFAULT_CLIENT_SERVICE_URLS,
        user_agent: str = DEFAULT_USER_AGENT,
        raise_exception: bool = DEFAULT_RAISE_EXCEPTION,
        timeout: typing.Union[int, float] = 10.0,
        use_fallback: bool = False,
    ) -> None:
        """
        Инициализация клиента с учётом заданных параметров.
        """
        self.loop = loop
        self.raise_exception = raise_exception

        if use_fallback:
            self.service_urls = DEFAULT_FALLBACK_SERVICE_URLS
            self.client_type = "gtx"
        else:
            self.service_urls = service_urls
            self.client_type = "tw-ob"

        if not _aclient:
            headers = {
                "User-Agent": user_agent,
                "Referer": "https://translate.google.com",
            }

            # Настройка прокси из переменных окружения
            proxies = None
            http_proxy = os.getenv("HTTP_PROXY")
            https_proxy = os.getenv("HTTPS_PROXY")
            if http_proxy or https_proxy:
                # Если https_proxy не задан, используем http_proxy для https
                proxies = {
                    "http://": http_proxy,
                    "https://": https_proxy if https_proxy is not None else http_proxy,
                }

            self._aclient = httpx.AsyncClient(
                headers=headers, timeout=timeout, proxies=proxies
            )
        else:
            self._aclient = _aclient

    async def close(self) -> None:
        """
        Закрыть httpx.AsyncClient
        """
        if self._aclient:
            await self._aclient.aclose()

    async def __aenter__(self) -> "Translator":
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.close()

    async def _build_rpc_request(self, text: str, dest: str, src: str) -> str:
        """
        Сформировать f.req для RPC запроса.
        """
        return json.dumps(
            [
                [
                    [
                        RPC_ID,
                        json.dumps(
                            [[text, src, dest, True], [None]], separators=(",", ":")
                        ),
                        None,
                        "generic",
                    ],
                ]
            ],
            separators=(",", ":"),
        )

    def _pick_service_url(self) -> str:
        """
        Выбрать случайный сервисный URL (или первый, если список один).
        """
        if len(self.service_urls) == 1:
            return self.service_urls[0]
        return random.choice(self.service_urls)

    async def _translate(
        self, text: str, dest: str, src: str
    ) -> typing.Tuple[str, httpx.Response]:
        """
        Вспомогательный метод, отправляющий POST-запрос к Google RPC и возвращающий сырой ответ.
        """
        url = urls.TRANSLATE_RPC.format(host=self._pick_service_url())
        data = {
            "f.req": await self._build_rpc_request(text, dest, src),
        }
        params = {
            "rpcids": RPC_ID,
            "bl": "boq_translate-webserver_20201207.13_p0",
            "soc-app": 1,
            "soc-platform": 1,
            "soc-device": 1,
            "rt": "c",
        }

        request = await self._aclient.post(url, params=params, data=data)
        status = (
            request.status_code if hasattr(request, "status_code") else request.status
        )

        if status != 200 and self.raise_exception:
            raise Exception(
                f"""Unexpected status code "{status}" from {self.service_urls}"""
            )
        return request.text, request

    def _find_translation_list(self, data):
        """
        Рекурсивный поиск списка переводов (как во втором варианте).

        Если в массиве встречается субмассив вида [["house","haus"], ["home","heim"], ...],
        возвращаем этот субмассив. Может применяться при переводе одного слова, где Google
        предоставляет несколько вариантов (masculine, feminine, и т.п.).
        """
        if isinstance(data, list):
            for item in data:
                if isinstance(item, list):
                    # Проверяем, что это список, где каждый элемент - тоже список, и в нём первая позиция - строка
                    if all(
                        isinstance(subitem, list)
                        and len(subitem) > 0
                        and isinstance(subitem[0], str)
                        for subitem in item
                    ):
                        return item
                    # Рекурсивно обходим
                    result = self._find_translation_list(item)
                    if result is not None:
                        return result
        return None

    async def translate(
        self, text: str, dest: str = "en", src: str = "auto"
    ) -> Translated:
        """
        Перевести текст с языка src на язык dest.

        Объединённая логика:
          1) Парсим ответ как в версии №1 (считаем квадратные скобки, RPC_ID).
          2) Пробуем найти список вариантов перевода (как в версии №2).
             - Если это перевод одного слова, где несколько вариантов, берём первый.
             - Если это целое предложение, то, скорее всего, найдём "части" (parsed[1][0][0][5]) и склеим.
        """
        # Приводим к нижнему регистру и убираем региональные коды (en_US -> en)
        dest = dest.lower().split("_", 1)[0]
        src = src.lower().split("_", 1)[0]

        if src != "auto" and src not in LANGUAGES:
            if src in SPECIAL_CASES:
                src = SPECIAL_CASES[src]
            elif src in LANGCODES:
                src = LANGCODES[src]
            else:
                raise ValueError(f"Invalid Source Language: {src}")

        if dest not in LANGUAGES:
            if dest in SPECIAL_CASES:
                dest = SPECIAL_CASES[dest]
            elif dest in LANGCODES:
                dest = LANGCODES[dest]
            else:
                raise ValueError(f"Invalid Destination Language: {dest}")

        origin = text
        data, response = await self._translate(text, dest, src)

        # --- (1) Как в первой версии: ищем блок JSON по RPC_ID и сводим скобки ---
        token_found = False
        square_bracket_counts = [0, 0]
        resp = ""

        for line in data.split("\n"):
            # Проверяем, встретили ли мы "MkEWBc" (RPC_ID)
            token_found = token_found or f'"{RPC_ID}"' in line[:30]
            if not token_found:
                continue

            is_in_string = False
            for index, char in enumerate(line):
                # Отслеживаем, находимся ли мы внутри кавычек, чтобы правильно считать скобки
                if char == '"' and (index == 0 or line[index - 1] != "\\"):
                    is_in_string = not is_in_string
                if not is_in_string:
                    if char == "[":
                        square_bracket_counts[0] += 1
                    elif char == "]":
                        square_bracket_counts[1] += 1

            resp += line
            if square_bracket_counts[0] == square_bracket_counts[1]:
                # «Сошлись» квадратные скобки
                break

        # Парсим вырезанный блок JSON
        try:
            block_data = json.loads(resp)
            parsed = json.loads(block_data[0][2])  # Основная полезная инфа
        except Exception as e:
            raise Exception(
                f"Error occurred while loading data: {e} \n Response : {response}"
            )

        # --- (2) Пытаемся найти список вариантов перевода через _find_translation_list ---
        translations = self._find_translation_list(parsed)

        if translations is None:
            # Если не нашли список вариантов для одного слова,
            # значит у нас, скорее всего, перевод фраз/предложений (как версия №1).
            # Применим «старый» способ — вытаскиваем части из parsed[1][0][0][5], если есть.
            try:
                should_spacing = parsed[1][0][0][3]
            except:
                should_spacing = False

            try:
                parts_raw = parsed[1][0][0][5]  # Список кусков перевода
            except:
                # Ничего не нашли, значит Google не вернул ожидаемую структуру
                parts_raw = []

            translated_parts: typing.List[TranslatedPart] = []
            for part in parts_raw:
                # part обычно выглядит как ["Переведённый кусок", ["какие-то данные"]]
                piece_text = part[0] if part and len(part) > 0 else ""
                synonyms = part[1] if part and len(part) > 1 else []
                translated_parts.append(TranslatedPart(piece_text, synonyms))

            # Склеиваем все куски
            translated_text = (" " if should_spacing else "").join(
                p.text for p in translated_parts
            )
        else:
            # Есть список вариантов (скорее всего перевод одного слова).
            # Выполним логику «берём первый» (или мужской, если нужно).
            if not isinstance(translations, list) or not translations:
                raise Exception("No valid translations found.")

            # Допустим, нам не нужно выделять (masculine)/(feminine) —
            # берём просто первый:
            selected_part = translations[0]

            # selected_part обычно что-то вроде ["house", "haʊs", "(noun)"] или ["casa", ...]
            if not isinstance(selected_part, list) or len(selected_part) < 1:
                raise Exception("Invalid translation structure.")

            translated_text = selected_part[0]
            # Произношение, если есть
            pronunciation = selected_part[1] if len(selected_part) > 1 else None

            # Делаем один TranslatedPart
            translated_parts = [TranslatedPart(text=translated_text, candidates=[])]

            # Можно дополнительно анализировать should_spacing (но для одного слова это не так важно)
            should_spacing = False

        # Дополнительно пытаемся определить конечный src, если он был "auto"
        if src == "auto":
            try:
                src = parsed[2]  # Иногда Google кладёт опред. язык сюда
            except:
                pass
        if src == "auto":
            try:
                # Ещё одна позиция, где может лежать язык
                src = parsed[0][2]
            except:
                pass

        # Пробуем вытащить произношение (из «старой» структуры).
        # Если мы уже нашли pronunciation выше (одиночное слово) — пусть останется.
        # Иначе пытаемся найти здесь.
        try:
            origin_pronunciation = parsed[0][0]
        except:
            origin_pronunciation = None

        if "pronunciation" not in locals():
            # Если нет переменной pronunciation, определим её как None
            pronunciation = None

        # Признак confidence (Google иногда возвращает, но не всегда)
        confidence = None

        extra_data = {
            "confidence": confidence,
            "parts": translated_parts,
            "origin_pronunciation": origin_pronunciation,
            "parsed": parsed,
        }

        result = Translated(
            src=src,
            dest=dest,
            origin=origin,
            text=translated_text,
            pronunciation=pronunciation,
            parts=translated_parts,
            extra_data=extra_data,
            response=response,
        )
        return result

    async def detect(self, text: str) -> Detected:
        """
        Определить язык текста.
        """
        translated = await self.translate(text, src="auto", dest="en")
        return Detected(
            lang=translated.src,
            confidence=translated.extra_data.get("confidence", None),
            response=translated._response,
        )
