"""One package per milestone. Pick one with `python -m eden <command> --stage <name>`."""

from . import m0, m1, mvp

STAGES = {mvp.NAME: mvp, m0.NAME: m0, m1.NAME: m1}
