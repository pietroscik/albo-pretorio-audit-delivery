"""
Optional dependency management with lazy loading.
This module provides safe imports for optional dependencies that may not be installed.
"""

import importlib
from typing import Any, Optional


def import_optional_dependency(name: str) -> Optional[Any]:
    """
    Safely import an optional dependency.
    
    Args:
        name: Name of the module to import
        
    Returns:
        Module object if import succeeds, None otherwise
    """
    try:
        return importlib.import_module(name)
    except ImportError:
        return None


# Lazy-loaded optional dependencies
def get_flask():
    """Lazy load Flask for web authentication."""
    return import_optional_dependency('flask')


def get_bcrypt():
    """Lazy load bcrypt for password hashing."""
    return import_optional_dependency('bcrypt')


def get_fuzzywuzzy():
    """Lazy load fuzzywuzzy for string similarity operations."""
    return import_optional_dependency('fuzzywuzzy')


def get_exceptions():
    """Lazy load exceptions module (local)."""
    try:
        from . import exceptions
        return exceptions
    except ImportError:
        return None


# Pre-computed availability flags
FLASK_AVAILABLE = get_flask() is not None
BCRYPT_AVAILABLE = get_bcrypt() is not None
FUZZYWUZZY_AVAILABLE = get_fuzzywuzzy() is not None
LOCAL_EXCEPTIONS_AVAILABLE = get_exceptions() is not None


def check_optional_deps():
    """Return a dictionary of available optional dependencies."""
    return {
        'flask': FLASK_AVAILABLE,
        'bcrypt': BCRYPT_AVAILABLE,
        'fuzzywuzzy': FUZZYWUZZY_AVAILABLE,
        'local_exceptions': LOCAL_EXCEPTIONS_AVAILABLE
    }


__all__ = [
    'import_optional_dependency',
    'get_flask',
    'get_bcrypt',
    'get_fuzzywuzzy',
    'get_exceptions',
    'FLASK_AVAILABLE',
    'BCRYPT_AVAILABLE',
    'FUZZYWUZZY_AVAILABLE',
    'LOCAL_EXCEPTIONS_AVAILABLE',
    'check_optional_deps'
]