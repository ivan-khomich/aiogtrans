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
from httpx import Proxy

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

            # Получаем настройки прокси из переменных окружения
            http_proxy = os.getenv("HTTP_PROXY")
            https_proxy = os.getenv("HTTPS_PROXY")

            if http_proxy and https_proxy and http_proxy == https_proxy:
                # Если для HTTP и HTTPS используется один и тот же прокси
                self._aclient = httpx.AsyncClient(
                    headers=headers, timeout=timeout, proxy=http_proxy
                )
            elif http_proxy or https_proxy:
                proxy_mounts = {}
                # Настройка различных транспортов для HTTP и HTTPS при необходимости
                if http_proxy:
                    proxy_mounts["http://"] = httpx.AsyncHTTPTransport(proxy=http_proxy)
                if https_proxy:
                    proxy_mounts["https://"] = httpx.AsyncHTTPTransport(
                        proxy=https_proxy
                    )
                self._aclient = httpx.AsyncClient(
                    headers=headers, timeout=timeout, mounts=proxy_mounts
                )
            else:
                self._aclient = httpx.AsyncClient(headers=headers, timeout=timeout)
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

        # Выводим информацию о запросе для отладки
        print("=== Debug: Отправка запроса ===")
        print("URL:", url)
        print("Параметры:", params)
        print("Данные:", data)

        response = await self._aclient.post(url, params=params, data=data)

        # Выводим статус ответа
        print("=== Debug: Получен ответ ===")
        print("Статус-код:", response.status_code)
        print("HTTP-версия:", response.http_version)

        # Ограничим вывод тела ответа, чтобы не засорить консоль большим текстом
        text_response = response.text
        print(
            "Часть тела ответа:", text_response, "...\n"
        )  # выводим первые 500 символов

        status = response.status_code

        if status != 200 and self.raise_exception:
            raise Exception(
                f"""Unexpected status code "{status}" from {self.service_urls}"""
            )
        return response.text, response

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
        Translate text
        """
        # Приведение языковых кодов к нужному формату
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

        token_found = False
        square_bracket_counts = [0, 0]
        resp = ""
        for line in data.split("\n"):
            token_found = token_found or f'"{RPC_ID}"' in line[:30]
            if not token_found:
                continue

            is_in_string = False
            for index, char in enumerate(line):
                # Проверка на начало и конец строки внутри кавычек
                if char == '"' and line[max(0, index - 1)] != "\\":
                    is_in_string = not is_in_string
                if not is_in_string:
                    if char == "[":
                        square_bracket_counts[0] += 1
                    elif char == "]":
                        square_bracket_counts[1] += 1

            resp += line
            if square_bracket_counts[0] == square_bracket_counts[1]:
                break

        try:
            data_parsed = json.loads(resp)
            parsed = json.loads(data_parsed[0][2])
        except Exception as e:
            raise Exception(
                f"Error occurred while loading data: {e} \n Response : {response}"
            )

        # Извлечение флага spacing и частей перевода
        should_spacing = parsed[1][0][0][3]
        translated_parts = list(
            map(
                lambda part: TranslatedPart(part[0], part[1] if len(part) >= 2 else []),
                parsed[1][0][0][5],
            )
        )

        # Объединение частей перевода в одну строку
        translated = (" " if should_spacing else "").join(
            map(lambda part: part.text, translated_parts)
        )

        # Определение исходного языка при автоопределении
        if src == "auto":
            try:
                src = parsed[2]
            except:
                pass
        if src == "auto":
            try:
                src = parsed[0][2]
            except:
                pass

        # Извлечение произношения, если доступно
        pronunciation = None
        try:
            pronunciation = parsed[1][0][0][1]
        except:
            pass

        # Попытка извлечения оригинального произношения
        origin_pronunciation = None
        try:
            origin_pronunciation = parsed[0][0]
        except:
            pass

        # Конфиденция перевода (не всегда доступна)
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
            text=translated,
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
