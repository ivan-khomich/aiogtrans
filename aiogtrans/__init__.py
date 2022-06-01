"""Free Google Translate API for Python. Translates totally free of charge."""
__all__ = ("Translator",)
__version__ = "1.0.1"

# Client
from aiogtrans.client import Translator

# Constants
from aiogtrans.constants import LANGCODES, LANGUAGES

# Models for typehinting
from aiogtrans.models import Translated, Detected
