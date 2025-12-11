"""
RyxSurf Features - Lazy-loaded browser features

All features are loaded on-demand to minimize memory usage.
"""

from .passwords import get_password_manager, unload_password_manager
from .autofill import get_autofill
from .pdf import get_pdf_viewer, unload_pdf_viewer
from .settings import SETTINGS_HTML, SEARCH_ENGINES, get_search_url

__all__ = [
    'get_password_manager',
    'unload_password_manager', 
    'get_autofill',
    'get_pdf_viewer',
    'unload_pdf_viewer',
    'SETTINGS_HTML',
    'SEARCH_ENGINES',
    'get_search_url',
]
