"""
pages - Wizard page components for inCODE NGX Configuration Tool
"""

from .welcome_page import WelcomePage
from .connection_page import ConnectionPage
from .inputs_page import InputsPage
from .confirmation_page import ConfirmationPage
from .write_page import WritePage

__all__ = [
    'WelcomePage',
    'ConnectionPage', 
    'InputsPage',
    'ConfirmationPage',
    'WritePage'
]

