"""M1: the agent decides how many events matter, by applying a significance rule to a pool of candidates.

Provides the same names as every stage (see eden/stages/mvp/__init__.py). `extract --stage m1` proposes
and pins the pool; `judge` then runs the significance test over it (see judge.py).
"""

from .prompt import DEFAULT_COUNT, PROMPT_VERSION, SYSTEM, TASK
from .render import render
from .schema import Event, EventList, ModelEvent
from .validate import validate

NAME = "m1"
