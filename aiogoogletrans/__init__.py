"""Free Google Translate API for Python. Translates totally free of charge."""
__all__ = 'Translator',
__version__ = '1.0.0'


from asyncgoogletrans.client import Translator
from asyncgoogletrans.constants import LANGCODES, LANGUAGES
from asyncgoogletrans.models import Translated, Detected