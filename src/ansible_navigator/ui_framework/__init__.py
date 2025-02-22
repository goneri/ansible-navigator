"""ui_framework
"""

from .content_defs import ContentBase
from .content_defs import ContentView
from .curses_defs import CursesLine
from .curses_defs import CursesLinePart
from .curses_defs import CursesLines
from .form import Form
from .form_utils import dict_to_form
from .form_utils import error_notification
from .form_utils import form_to_dict
from .form_utils import nonblocking_notification
from .form_utils import warning_notification
from .ui import Action
from .ui import Content
from .ui import Interaction
from .ui import Menu
from .ui import UIConfig
from .ui import UserInterface
from .ui_constants import Color
from .ui_constants import Decoration


__all__ = (
    "Action",
    "Color",
    "Content",
    "ContentBase",
    "ContentView",
    "CursesLine",
    "CursesLinePart",
    "CursesLines",
    "Decoration",
    "dict_to_form",
    "error_notification",
    "form_to_dict",
    "Form",
    "Interaction",
    "Menu",
    "nonblocking_notification",
    "UIConfig",
    "UserInterface",
    "warning_notification",
)
