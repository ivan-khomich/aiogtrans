"""
Copyright (c) 2022 Ben Z

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.
"""

import typing

from aiohttp import ClientResponse
from httpx import Response


class Base:
    """
    Base class for response objects such as Translated and Detected
    """

    __slots__ = "_response"

    def __init__(self, response: typing.Union[Response, ClientResponse] = None) -> None:
        """
        Base class for basically all objects
        """
        self._response = response


class TranslatedPart:
    """
    Translated parts
    """

    __slots__ = ("text", "candidates")

    def __init__(self, text: str, candidates: typing.List[str]) -> None:
        """
        Init for translated parts
        """
        self.text = text
        self.candidates = candidates

    def __str__(self) -> str:
        return self.text

    def __dict__(self) -> dict:
        return {
            "text": self.text,
            "candidates": self.candidates,
        }


class Translated(Base):
    """
    Translate result object

    :param src: source language (default: auto)
    :param dest: destination language (default: en)
    :param origin: original text
    :param text: translated text
    :param pronunciation: pronunciation
    """

    __slots__ = (
        "src",
        "dest",
        "origin",
        "text",
        "pronunciation",
        "extra_data",
        "parts",
    )

    def __init__(
        self,
        src: str,
        dest: str,
        origin: str,
        text: str,
        pronunciation: str,
        parts: typing.List[TranslatedPart],
        extra_data=None,
        **kwargs,
    ) -> None:
        """
        Init for translated object
        """
        super().__init__(**kwargs)
        self.src = src
        self.dest = dest
        self.origin = origin
        self.text = text
        self.pronunciation = pronunciation
        self.parts = parts
        self.extra_data = extra_data

    def __str__(self) -> str:
        return self.__unicode__()

    def __unicode__(self) -> str:
        return f"Translated(src={self.src}, dest={self.dest}, text={self.text}, pronunciation={self.pronunciation}, extra_data={repr(self.extra_data)[:10]}...)"

    def __dict__(self) -> dict:
        return {
            "src": self.src,
            "dest": self.dest,
            "origin": self.origin,
            "text": self.text,
            "pronunciation": self.pronunciation,
            "extra_data": self.extra_data,
            "parts": list(map(lambda part: part.__dict__(), self.parts)),
        }


class Detected(Base):
    """
    Language detection result object

    :param lang: detected language
    :param confidence: the confidence of detection result (0.00 to 1.00)
    """

    __slots__ = ("lang", "confidence")

    def __init__(self, lang: str, confidence: float, **kwargs) -> None:
        """
        Init for detected object
        """
        super().__init__(**kwargs)
        self.lang = lang
        self.confidence = confidence

    def __str__(self) -> str:
        return self.__unicode__()

    def __unicode__(self) -> str:
        return f"Detected(lang={self.lang}, confidence={self.confidence})"
