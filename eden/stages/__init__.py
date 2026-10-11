"""One package per milestone. Pick one with `python -m eden <command> --stage <name>`."""

from . import mvp

STAGES = {mvp.NAME: mvp}
