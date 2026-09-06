"""Presentation layer for the histopathology triage console.

    tokens      design tokens -- colour, type, motion, radii
    theme       token -> stylesheet injection
    components  reusable HTML/SVG components
    charts      themed Plotly figures
    copy        every piece of substantial user-facing prose
"""

from . import charts, components, copy, theme, tokens  # noqa: F401

__all__ = ["charts", "components", "copy", "theme", "tokens"]
