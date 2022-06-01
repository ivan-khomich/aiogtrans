"""Free Google Translate API for Python. Translates totally free of charge."""
__all__ = 'Translator',
__version__ = '1.0.0'


from aiogoogletrans.client import Translator
from aiogoogletrans.constants import LANGCODES, LANGUAGES
from aiogoogletrans.models import Translated, Detected