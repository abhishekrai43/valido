from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class BBox:
    """Bounding box in PDF coordinate space used by pdfplumber.

    pdfplumber uses a coordinate system with origin near top-left for many
    properties (top/bottom), but the numeric values are consistent within a
    page. We treat the coordinates purely geometrically.
    """

    x0: float
    top: float
    x1: float
    bottom: float

    @property
    def width(self) -> float:
        return max(0.0, self.x1 - self.x0)

    @property
    def height(self) -> float:
        return max(0.0, self.bottom - self.top)

    @property
    def cx(self) -> float:
        return (self.x0 + self.x1) / 2.0

    @property
    def cy(self) -> float:
        return (self.top + self.bottom) / 2.0


@dataclass(frozen=True)
class Word:
    text: str
    bbox: BBox


@dataclass(frozen=True)
class VerticalLine:
    """A vertical border line segment (x constant)."""

    x: float
    top: float
    bottom: float


@dataclass(frozen=True)
class HorizontalLine:
    """A horizontal border line segment (y constant)."""

    y: float
    x0: float
    x1: float
