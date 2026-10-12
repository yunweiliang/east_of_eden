"""One package per milestone. Pick one with `python -m eden <command> --stage <name>`."""

from . import m0, mvp

STAGES = {mvp.NAME: mvp, m0.NAME: m0}
