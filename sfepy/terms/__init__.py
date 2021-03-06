import sfepy
import terms
import extmods
from terms import Terms, Term, CharacteristicFunction, vector_chunk_generator
from cache import DataCache, DataCaches
from sfepy.base.base import load_classes

term_files = sfepy.get_paths('sfepy/terms/terms*.py')
term_table = load_classes(term_files, [Term], ignore_errors=True)

cache_files = sfepy.get_paths('sfepy/terms/caches*.py')
cache_table = load_classes(cache_files, [DataCache], ignore_errors=True)
del sfepy

def register_term(cls):
    """
    Register a custom term.
    """
    term_table[cls.name] = cls
