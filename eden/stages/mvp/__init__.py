"""MVP: 10 linear events leading to Cal's reveal.

Every stage package exposes the same names, so the shared code in eden/core can run any of them:
  NAME, DEFAULT_COUNT, PROMPT_VERSION, SYSTEM, TASK   what to ask the model
  ModelEvent, Event, EventList                        the schema (model-facing, stored, list wrapper)
  validate(events, count) -> Report                   checks; errors trigger a repair turn
  render(events, meta, out_dir) -> list[Path]         writes the output files
"""

from .prompt import DEFAULT_COUNT, PROMPT_VERSION, SYSTEM, TASK
from .render import render, to_portfolio_timeline
from .schema import Event, EventList, ModelEvent
from .validate import validate

NAME = "mvp"
