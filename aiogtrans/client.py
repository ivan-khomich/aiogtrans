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

EXCLUDES = ("en", "ca", "fr")
RPC_ID = "MkEWBc"


class Translator:
    """
    Google Translate Ajax API Translator class

    Create an instance of this class to access the API.
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
        Initiating the client with the given parameters.
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

            # Настройка прокси
            proxies = None
            http_proxy = os.getenv('HTTP_PROXY')
            https_proxy = os.getenv('HTTPS_PROXY')
            if http_proxy or https_proxy:
                proxies = {
                    "http://": http_proxy,
                    "https://": https_proxy if https_proxy is not None else http_proxy,
                }

            self._aclient = httpx.AsyncClient(headers=headers, timeout=timeout, proxies=proxies)
        else:
            self._aclient = _aclient

    async def close(self) -> None:
        """
        Close the client
        """
        if self._aclient:
            await self._aclient.aclose()

    async def __aenter__(self) -> "Translator":
        """
        Enter the context
        """
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """
        Exit the context
        """
        await self.close()

    async def _build_rpc_request(self, text: str, dest: str, src: str) -> str:
        """
        Build the rpc request
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
        Pick a service url
        """
        if len(self.service_urls) == 1:
            return self.service_urls[0]
        return random.choice(self.service_urls)

    async def _translate(
        self, text: str, dest: str, src: str
    ) -> typing.Tuple[str, httpx.Response]:
        """
        Translate protected method
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
        status = request.status_code if hasattr(request, "status_code") else request.status
        if status != 200 and self.raise_exception:
            raise Exception(
                f"""Unexpected status code "{status}" from {self.service_urls}"""
            )
        text = request.text
        return text, request

    async def _parse_extra_data(self, data: list) -> dict:
        """
        Parsing extra data to be returned to the user
        """
        response_parts_name_mapping = {
            0: "translation",
            1: "all-translations",
            2: "original-language",
            5: "possible-translations",
            6: "confidence",
            7: "possible-mistakes",
            8: "language",
            11: "synonyms",
            12: "definitions",
            13: "examples",
            14: "see-also",
        }

        extra = {}

        for index, category in response_parts_name_mapping.items():
            extra[category] = (
                data[index] if (index < len(data) and data[index]) else None
            )

        return extra

    def _find_translation_list(self, data):
        """
        Recursively search for the translation list in the parsed data
        """
        if isinstance(data, list):
            for item in data:
                if isinstance(item, list):
                    # Check if this is a list of translations
                    if all(isinstance(subitem, list) and len(subitem) > 0 and isinstance(subitem[0], str) for subitem in item):
                        return item
                    # Recurse into the item
                    result = self._find_translation_list(item)
                    if result:
                        return result
        return None

    async def translate(
        self, text: str, dest: str = "en", src: str = "auto"
    ) -> Translated:
        """
        Translate text
        """
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
                if char == '"' and (index == 0 or line[index - 1] != "\\"):
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
            data = json.loads(resp)
            parsed = json.loads(data[0][2])
            print(f"Parsed response: {parsed}")  # Отладочный вывод
        except Exception as e:
            print(f"Error occurred while loading data: {e}")
            print(f"Response: {response}")
            raise Exception(
                f"Error occurred while loading data: {e} \n Response : {response}"
            )

        # Рекурсивный поиск переводов
        translations = self._find_translation_list(parsed)
        if translations is None:
            print("Failed to extract translations from the response.")  # Отладочный вывод
            raise Exception("Failed to extract translations from the response.")
        
        print(f"Found translations: {translations}")  # Отладочный вывод

        if not isinstance(translations, list):
            print("Translations format is invalid.")  # Отладочный вывод
            raise Exception("Translations format is invalid.")

        # Фильтрация переводов с мужским родом
        masculine_translations = [
            part for part in translations
            if isinstance(part, list) and len(part) > 2 and part[2] == "(masculine)"
        ]

        print(f"Masculine translations: {masculine_translations}")  # Отладочный вывод

        if masculine_translations:
            selected_part = masculine_translations[0]
            print(f"Selected masculine translation: {selected_part}")  # Отладочный вывод
        elif translations:
            selected_part = translations[0]
            print(f"Selected first available translation: {selected_part}")  # Отладочный вывод
        else:
            # Нет переводов, хотя должно быть
            print("No translation entries found.")  # Отладочный вывод
            raise Exception("No translation entries found.")

        # Проверка структуры выбранного перевода
        if not isinstance(selected_part, list) or len(selected_part) < 1:
            print("Selected translation part is invalid.")  # Отладочный вывод
            raise Exception("Selected translation part is invalid.")

        # Извлечение текста перевода
        translated_text = selected_part[0] if selected_part[0] else "Translation Failed"

        # Извлечение произношения, если доступно
        pronunciation = selected_part[1] if len(selected_part) > 1 and selected_part[1] else None

        # Создание объекта TranslatedPart без аргумента synonyms
        # Передаём 'candidates' как пустой список
        translated_parts = [
            TranslatedPart(
                text=translated_text,
                candidates=[]  # Передаём пустой список, если не нужны кандидаты
            )
        ]

        # Определение should_spacing
        should_spacing = False  # По умолчанию
        try:
            # Поиск should_spacing в parsed, если возможно
            should_spacing = parsed[6][3] if len(parsed) > 6 and isinstance(parsed[6], list) and len(parsed[6]) > 3 else False
        except (IndexError, TypeError):
            print("Could not find should_spacing, defaulting to False")  # Отладочный вывод

        translated = (" " if should_spacing else "").join(
            map(lambda part: part.text, translated_parts)
        )

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

        # currently not available
        confidence = None

        origin_pronunciation = None
        try:
            origin_pronunciation = parsed[0][0]
        except:
            pass

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
        Detect a language
        """
        translated = await self.translate(text, src="auto", dest="en")
        result = Detected(
            lang=translated.src,
            confidence=translated.extra_data.get("confidence", None),
            response=translated._response,
        )
        return result
