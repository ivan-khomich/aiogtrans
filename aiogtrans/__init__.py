"""Free Google Translate API for Python. Translates totally free of charge."""
__all__ = 'Translator',
__version__ = '1.0.0'


from aiogtrans.client import Translator
from aiogtrans.constants import LANGCODES, LANGUAGES
from aiogtrans.models import Translated, Detected