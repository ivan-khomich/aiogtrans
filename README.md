# aiogtrans

aiogtrans is a **free** and **unlimited** python library that implements the Google Translate API asynchronously. This uses the [Google Translate Ajax API](https://translate.google.com>) and [httpx](https://www.python-httpx.org) to make api calls.

Compatible with Python 3.6+.

For details refer to the [API Documentation](https://aiogtrans.readthedocs.io/en/latest>).

## Features

-  Fast and semi-reliable
	- Uses the same api that google translate uses
	- Reverse Engineered
-  Auto language detection
-  Bulk translations
-  Customizable service URL
-  HTTP/2 support

## HTTP/2 support

This library uses httpx for HTTP requests so HTTP/2 is supported by default.

You can check if http2 is enabled and working by the `._response.http_version` of `Translated` or `Detected` object:

```py
>>> (await translator.translate('테스트'))._response.http_version
# 'HTTP/2'
```

### How does this library work?

You may wonder why this library works properly, whereas other approaches such like goslate won't work since Google has updated its translation service recently with a ticket mechanism to prevent a lot of crawler programs.

The original fork author [Suhun Han](https://github.com/ssut) eventually figured out a way to generate a ticket by reverse engineering the obfuscated and minified code used by Google to generate tokens [https://translate.google.com/translate/releases/twsfe_w_20170306_RC00/r/js/desktop_module_main.js>](https://translate.google.comtranslate/releases/twsfe_w_20170306_RC00/r/js/desktop_module_main.js>), and implemented this in Python. However, this could be blocked at any time.

### Why not use googletrans?

It seems [Suhun Han](https://github.com/ssut) has abandoned the project, at the time of this writing it's been nearly a year and a half since the last commit.

I have decided to move on and update this project.

## Installation

```bash
$ pip install aiogtrans
```

## Basic Usage

If a source language is not given, google translate attempts to detect the source language.

```python
>>> from aiogtrans import Translator
>>> translator = Translator()
>>> await translator.translate('안녕하세요.')
# <Translated src=ko dest=en text=Good evening. pronunciation=Good evening.>
>>> await translator.translate('안녕하세요.', dest='ja')
# <Translated src=ko dest=ja text=こんにちは。 pronunciation=Kon'nichiwa.>
>>> await translator.translate('veritas lux mea', src='la')
# <Translated src=la dest=en text=The truth is my light pronunciation=The truth is my light>
```

### Customize service URL

You can use another google translate domain for translation. If multiple URLs are provided, the program will randomly choose a domain.

```python
>>> from aiogtrans import Translator
>>> translator = Translator(service_urls=[
        'translate.google.com',
        'translate.google.co.kr',
    ])
```

### Advanced Usage (Bulk Translations)

You can provide a list of strings to be used to translated in a single method and HTTP session. 

```python
>>> translations = await translator.translate(['The quick brown fox', 'jumps over', 'the lazy dog'], dest='ko')
>>> for translation in translations:
...    print(translation.origin, ' -> ', translation.text)
# The quick brown fox  ->  빠른 갈색 여우
# jumps over  ->  이상 점프
# the lazy dog  ->  게으른 개
```

### Language Detection

The detect method, as its name implies, identifies the language used in a given sentence.

```python
>>> from googletrans import Translator
>>> translator = Translator()
>>> await translator.detect('이 문장은 한글로 쓰여졌습니다.')
# <Detected lang=ko confidence=0.27041003>
>>> await translator.detect('この文章は日本語で書かれました。')
# <Detected lang=ja confidence=0.64889508>
>>> await translator.detect('This sentence is written in English.')
# <Detected lang=en confidence=0.22348526>
>>> await translator.detect('Tiu frazo estas skribita en Esperanto.')
# <Detected lang=eo confidence=0.10538048>
```

## aiogtrans as a command line application

```bash
$ translate -h
usage: translate [-h] [-d DEST] [-s SRC] [-c] text

Python Google Translator as a command-line tool

positional arguments:
    text                  The text you want to translate.

optional arguments:
    -h, --help            show this help message and exit
    -d DEST, --dest DEST  The destination language you want to translate.
                        (Default: en)
    -s SRC, --src SRC     The source language you want to translate. (Default:
                        auto)
    -c, --detect

$ translate "veritas lux mea" -s la -d en
[veritas] veritas lux mea
    ->
[en] The truth is my light
[pron.] The truth is my light

$ translate -c "안녕하세요."
[ko, 1] 안녕하세요.
```

## Note on Library Usage

**DISCLAIMER**: this is an unofficial library using the web API of translate.google.com and also is not associated with Google.

-  **The maximum character limit on a single text is 15,000.**

-  Due to limitations of the web version of google translate, this API does not guarantee that the library would work properly at all times (so please use this library if you don't care about stability).

-  **Important:** If you want to use a stable API, it is highly recommended that you use Google's official translate API [https://cloud.google.com/translate/docs](https://cloud.google.com/translate/docs).

-  If you get HTTP 5xx error or errors like #6, it's probably because Google has banned your client IP address.

## Contributing

Contributions are currently discouraged, I am writing this fork as a personal project and if I ever do decide to open up to contributions I will change this.

Of course you're more then welcome to fork this and make your own changes

## License

**aiogtrans** is licensed under the MIT License. The terms are as follows:

The MIT License (MIT)

Copyright (c) 2022 Ben Zhou 

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
