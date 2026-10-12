"""M0: 20 events with causes and threads, converging on Cal's reveal.

Provides the same names as every stage (see eden/stages/mvp/__init__.py).
"""

from .prompt import DEFAULT_COUNT, PROMPT_VERSION, SYSTEM, TASK
from .render import render
from .schema import Event, EventList, ModelEvent
from .validate import validate

NAME = "m0"
