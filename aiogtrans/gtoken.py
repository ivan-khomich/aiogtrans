# -*- coding: utf-8 -*-
import ast
import asyncio
import math
import re
import time

import httpx

from aiogtrans.utils import rshift


class TokenGenerator:
    """Google Translate API token generator

    translate.google.com uses a token to authorize the requests. If you are
    not Google, you do have this token and will have to pay for use.
    This class is the result of reverse engineering on the obfuscated and
    minified code used by Google to generate such token.

    The token is based on a seed which is updated once per hour and on the
    text that will be translated.
    Both are combined - by some strange math - in order to generate a final
    token (e.g. 744915.856682) which is used by the API to validate the
    request.

    This operation will cause an additional request to get an initial
    token from translate.google.com.

    Example usage:
        >>> from googletrans.gtoken import TokenAcquirer
        >>> acquirer = TokenAcquirer()
        >>> text = 'test'
        >>> tk = acquirer.do(text)
        >>> tk
        950629.577246
    """

    RE_TKK = re.compile(r"tkk:\'(.+?)\'", re.DOTALL)
    RE_RAWTKK = re.compile(r"tkk:\'(.+?)\'", re.DOTALL)

    def __init__(self, loop: asyncio.AbstractEventLoop, client: httpx.AsyncClient, tkk: str = "0", host: str = "translate.google.com") -> None:
        """Initiation for the token generator"""
        self.loop = loop
        self.client = client
        self.tkk = tkk
        self.host = host if "http" in host else "https://" + host

    async def _update(self):
        """
        update tkk
        """
        # we don't need to update the base TKK value when it is still valid
        now = math.floor(int(time.time() * 1000) / 3600000.0)
    
        if self.tkk and int(self.tkk.split(".")[0]) == now:
            return

        r = await self.client.get(self.host)

        raw_tkk = self.RE_TKK.search(r.text)
    
        if raw_tkk:
            self.tkk = raw_tkk.group(1)
            return

        try:
            # this will be the same as python code after stripping out a reserved word 'var'
            code = self.RE_TKK.search(r.text).group(1).replace("var ", "")
            # unescape special ascii characters such like a \x3d(=)
            code = code.encode().decode("unicode-escape")

        except AttributeError:
            raise Exception(
                "Could not find TKK token for this request.\nSee https://github.com/ssut/py-googletrans/issues/234 for more details."
            )

        except:
            raise

        if code:
            tree = ast.parse(code)
            visit_return = False
            operator = "+"
            n, keys = 0, dict(a=0, b=0)
            for node in ast.walk(tree):
                if isinstance(node, ast.Assign):
                    name = node.targets[0].id
                    if name in keys:
                        if isinstance(node.value, ast.Num):
                            keys[name] = node.value.n
                        # the value can sometimes be negative
                        elif isinstance(node.value, ast.UnaryOp) and isinstance(
                            node.value.op, ast.USub
                        ):  # pragma: nocover
                            keys[name] = -node.value.operand.n
                elif isinstance(node, ast.Return):
                    # parameters should be set after this point
                    visit_return = True
                elif visit_return and isinstance(node, ast.Num):
                    n = node.n
                elif visit_return and n > 0:
                    # the default operator is '+' but implement some more for
                    # all possible scenarios
                    if isinstance(node, ast.Add):  # pragma: nocover
                        pass
                    elif isinstance(node, ast.Sub):  # pragma: nocover
                        operator = "-"
                    elif isinstance(node, ast.Mult):  # pragma: nocover
                        operator = "*"
                    elif isinstance(node, ast.Pow):  # pragma: nocover
                        operator = "**"
                    elif isinstance(node, ast.BitXor):  # pragma: nocover
                        operator = "^"
            # a safety way to avoid Exceptions
            clause = compile(
                "{1}{0}{2}".format(operator, keys["a"], keys["b"]), "", "eval"
            )
            value = eval(clause, dict(__builtin__={}))
            result = "{}.{}".format(n, value)

            self.tkk = result

    async def _xr(self, a, b):
        """Math for generating the token"""
        size_b = len(b)
        c = 0
        while c < size_b - 2:
            d = b[c + 2]
            d = ord(d[0]) - 87 if "a" <= d else int(d)
            d = rshift(a, d) if "+" == b[c + 1] else a << d
            a = a + d & 4294967295 if "+" == b[c] else a ^ d

            c += 3
        return a

    async def generate(self, text: str) -> str:
        a = []

        for i in text:
            val = ord(i)
            if val < 0x10000:
                a += [val]
            else:
                a += [
                    math.floor((val - 0x10000) / 0x400 + 0xD800),
                    math.floor((val - 0x10000) % 0x400 + 0xDC00),
                ]

        b = self.tkk if self.tkk != "0" else ""
        d = b.split(".")
        b = int(d[0]) if len(d) > 1 else 0

        e = []
        g = 0
        size = len(a)
        while g < size:
            l = a[g]
            if l < 128:
                e.append(l)
            else:
                if l < 2048:
                    e.append(l >> 6 | 192)
                else:
                    if (
                        (l & 64512) == 55296
                        and g + 1 < size
                        and a[g + 1] & 64512 == 56320
                    ):
                        g += 1
                        l = (
                            65536 + ((l & 1023) << 10) + (a[g] & 1023)
                        )
                        e.append(l >> 18 | 240)
                        e.append(l >> 12 & 63 | 128)
                    else:
                        e.append(l >> 12 | 224)
                    e.append(l >> 6 & 63 | 128)
                e.append(l & 63 | 128)
            g += 1
        a = b
        for i, value in enumerate(e):
            a += value
            a = await self._xr(a, "+-a^+6")
        a = await self._xr(a, "+-3^+b+-f")
        a ^= int(d[1]) if len(d) > 1 else 0
        if a < 0:
            a = (a & 2147483647) + 2147483648
        a %= 1000000

        token = f"{a}.{a ^ b}"
        return token

    async def do(self, text):
        await self._update()
        token = await self.generate(text)
        return token
