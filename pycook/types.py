from enum import Enum
from functools import total_ordering
from typing import Iterable, Optional, Union

from pydantic import BaseModel


class Position(BaseModel):
    row: int
    start: int
    length: int


class Units(Enum):
    gram = "g"
    kilogram = "kg"
    milligram = "mg"
    liter = "l"
    milliliter = "ml"
    second = "s"
    minute = "min"
    hour = "h"
    pinch = "pinch"
    teaspoon = "tsp"
    tablespoon = "tbsp"
    can = "can"
    clove = "clove"
    leave = "leave"
    pack = "pack"
    pod = "pod"


@total_ordering
class Unit(BaseModel):
    unit: Units
    amount: Union[float, int]

    def __lt__(self, other):
        return self.amount < other

    def __eq__(self, other):
        return self.amount == other and self.unit == other.unit

    def __str__(self):
        return f"{self.amount} {self.unit.value}"


@total_ordering
class PositionEvent(BaseModel):
    position: Position

    def __eq__(self, other):
        return (
            self.position.start == other.position.start
            and self.position.length == other.position.length
        )

    def __lt__(self, other):
        return self.position.start < other.position.start


class Ingredient(PositionEvent):
    name: str
    unit: Optional[Union[int, float, Unit]] = None

    def __str__(self):
        if self.unit is None:
            return self.name
        else:
            return f"{self.unit} {self.name}"

    def to_tex(self):
        # \ingredient[250]{g}{eggs}
        if self.unit is None:
            return f"\\ingredient[]{{}}{{{self.name}}}"
        elif isinstance(self.unit, Unit):
            return f"\\ingredient[{self.unit.amount}]{{{self.unit.unit.value}}}{{{self.name}}}"
        else:
            return f"\\ingredient[{self.unit}]{{}}{{{self.name}}}"


class Cookware(PositionEvent):
    name: str
    unit: Optional[Union[int, float]] = None

    def __str__(self):
        if self.unit is None:
            return self.name
        else:
            return f"{self.unit} {self.name}"


class Timer(PositionEvent):
    name: str
    unit: Unit

    def __str__(self):
        return f"{self.unit.amount} {self.unit.unit.value}"


class PositionEventEnum(Enum):
    Timer = "~"
    Cookware = "#"
    Ingredient = "@"


class Metadata(BaseModel):
    key: str
    value: str

    def __str__(self):
        return f"{self.key}: {self.value}"


class RowType(Enum):
    metadata = "metadata"
    comment = "comment"
    step = "step"


class InlineComment(PositionEvent):
    text: str


class SimpleRow(BaseModel):
    id: int
    text: str
    type: RowType


class TextRow(SimpleRow):
    ingredients: list[Ingredient]
    cookware: list[Cookware]
    timers: list[Timer]
    comments: list[InlineComment]

    def _replace_all_entryes(
        self, entries: Iterable[Union[Ingredient, Cookware, Timer]], bold: bool = False
    ) -> str:
        sorted_entries = sorted(entries, reverse=True)
        line = self.text
        for entry in sorted_entries:
            line = self._replace_entry(
                line, entry, bold=bold and isinstance(entry, Ingredient)
            )
        return line

    def _replace_entry(
        self, line: str, entry: Union[Ingredient, Cookware, Timer], bold: bool = False
    ) -> str:
        bold_chars = "**" if bold else ""

        return (
            line[: entry.position.start]
            + bold_chars
            + str(entry)
            + bold_chars
            + line[entry.position.start + entry.position.length :]
        )

    def __str__(self):
        return self._replace_all_entryes(
            self.ingredients + self.cookware + self.timers, bold=True
        )

    def to_tex(self):
        return self._replace_all_entryes(
            self.ingredients + self.cookware + self.timers, bold=True
        )


class Step(BaseModel):
    id: int
    rows: list[Union[TextRow, SimpleRow]]

    def __str__(self):
        return "\n".join([str(row) for row in self.rows])

    def to_tex(self):
        return "\n".join([row.to_tex() for row in self.rows])
