import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

import yaml


@dataclass
class Ingredient:
    """Represents a recipe ingredient with optional quantity and unit"""

    name: str
    quantity: Optional[Union[int, float, str]] = None
    unit: Optional[str] = None
    preparation: Optional[str] = None

    def __str__(self) -> str:
        result = self.name
        if self.quantity:
            result = f"{self.quantity} {self.unit or ''} {result}".strip()
        if self.preparation:
            result += f" ({self.preparation})"
        result = result.replace("  ", " ")
        return result


@dataclass
class Cookware:
    """Represents cookware needed for the recipe"""

    name: str
    quantity: Optional[Union[int, str]] = None

    def __str__(self) -> str:
        if self.quantity:
            return f"{self.quantity} {self.name}"
        return self.name


@dataclass
class Timer:
    """Represents a cooking timer"""

    name: Optional[str] = None
    duration: Optional[Union[int, float, str]] = None
    unit: Optional[str] = None

    def __str__(self) -> str:
        if self.duration:
            return f"{self.duration} {self.unit or ''}".strip()
        return ""


@dataclass
class Comment:
    """Represents a comment in the recipe"""

    text: str
    is_block: bool = False


@dataclass
class Note:
    """Represents a recipe note (lines starting with >)"""

    text: str


@dataclass
class Section:
    """Represents a recipe section (lines with == markers)"""

    title: str
    level: int = 1


# Token-based approach to maintain position and context
@dataclass
class Token:
    """Base class for all parsed tokens"""

    text: str
    start_pos: int
    end_pos: int

    def to_cooklang(self) -> str:
        """Convert back to Cooklang markup"""
        return self.text

    def to_markdown(self) -> str:
        """Convert to Markdown format"""
        return self.text

    def to_plain_text(self) -> str:
        """Convert to plain text"""
        return self.text

    def to_html(self) -> str:
        """Convert to HTML format"""
        return self.text


@dataclass
class TextToken(Token):
    """Plain text token"""

    pass


@dataclass
class IngredientToken(Token):
    """Ingredient token that maintains original markup and parsed data"""

    ingredient: Ingredient

    def to_cooklang(self) -> str:
        return self.text  # Keep original markup

    def to_markdown(self) -> str:
        result = f"**{self.ingredient.name}**"
        if self.ingredient.quantity:
            result = f"**{self.ingredient.quantity} {self.ingredient.unit or ''} {self.ingredient.name}**".strip()
        if self.ingredient.preparation:
            result += f" *({self.ingredient.preparation})*"
        result = result.replace("  ", " ")
        return result

    def to_plain_text(self) -> str:
        return str(self.ingredient)

    def to_html(self) -> str:
        result = f"<strong>{self.ingredient.name}</strong>"
        if self.ingredient.quantity:
            result = f"<strong>{self.ingredient.quantity} {self.ingredient.unit or ''} {self.ingredient.name}</strong>".strip()
        if self.ingredient.preparation:
            result += f" <em>({self.ingredient.preparation})</em>"
        return result


@dataclass
class CookwareToken(Token):
    """Cookware token"""

    cookware: Cookware

    def to_cooklang(self) -> str:
        return self.text

    def to_markdown(self) -> str:
        return f"*{self.cookware.name}*"

    def to_plain_text(self) -> str:
        return str(self.cookware)

    def to_html(self) -> str:
        if self.cookware.quantity:
            return f"<em>{self.cookware.quantity} {self.cookware.name}</em>"
        return f"<em>{self.cookware.name}</em>"


@dataclass
class TimerToken(Token):
    """Timer token"""

    timer: Timer

    def to_cooklang(self) -> str:
        return self.text

    def to_markdown(self) -> str:
        return f"**{self.timer}**"

    def to_plain_text(self) -> str:
        return str(self.timer)

    def to_html(self) -> str:
        return f"<em>{self.timer}</em>" if str(self.timer) else ""


@dataclass
class CommentToken(Token):
    """Comment token"""

    comment: Comment

    def to_cooklang(self) -> str:
        return self.text

    def to_markdown(self) -> str:
        if self.comment.is_block:
            return f"<!-- {self.comment.text} -->"
        return f"*({self.comment.text})*"

    def to_plain_text(self) -> str:
        return ""  # Comments don't appear in plain text

    def to_html(self) -> str:
        if self.comment.is_block:
            return f"<!-- {self.comment.text} -->"
        return f"<em>({self.comment.text})</em>"


@dataclass
class NoteToken(Token):
    """Note token"""

    note: Note

    def to_cooklang(self) -> str:
        return self.text

    def to_markdown(self) -> str:
        return f"> {self.note.text}"

    def to_plain_text(self) -> str:
        return self.note.text

    def to_html(self) -> str:
        return f"<blockquote>{self.note.text}</blockquote>"


@dataclass
class Step:
    """Represents a cooking step as a sequence of tokens"""

    tokens: List[Token] = field(default_factory=list)
    section: Optional[Section] = None

    @property
    def text(self) -> str:
        """Get the original text"""
        return "".join(token.text for token in self.tokens)

    @property
    def ingredients(self) -> List[Ingredient]:
        """Get all ingredients in this step"""
        return [
            token.ingredient
            for token in self.tokens
            if isinstance(token, IngredientToken)
        ]

    @property
    def cookware(self) -> List[Cookware]:
        """Get all cookware in this step"""
        return [
            token.cookware for token in self.tokens if isinstance(token, CookwareToken)
        ]

    @property
    def timers(self) -> List[Timer]:
        """Get all timers in this step"""
        return [token.timer for token in self.tokens if isinstance(token, TimerToken)]

    @property
    def comments(self) -> List[Comment]:
        """Get all comments in this step"""
        return [
            token.comment for token in self.tokens if isinstance(token, CommentToken)
        ]

    def to_cooklang(self) -> str:
        """Convert back to Cooklang markup"""
        return "".join(token.to_cooklang() for token in self.tokens)

    def to_markdown(self) -> str:
        """Convert to Markdown format"""
        return "".join(token.to_markdown() for token in self.tokens)

    def to_plain_text(self) -> str:
        """Convert to plain text"""
        return "".join(token.to_plain_text() for token in self.tokens)

    def to_html(self) -> str:
        return "".join(token.to_html() for token in self.tokens)


@dataclass
class Recipe:
    """Complete parsed recipe"""

    title: Optional[str] = None
    metadata: Dict = field(default_factory=dict)
    steps: List[Step] = field(default_factory=list)
    sections: List[Section] = field(default_factory=list)

    @property
    def ingredients(self) -> List[Ingredient]:
        """Get all unique ingredients from all steps"""
        all_ingredients = []
        for step in self.steps:
            all_ingredients.extend(step.ingredients)
        return self._deduplicate_ingredients(all_ingredients)

    @property
    def cookware(self) -> List[Cookware]:
        """Get all unique cookware from all steps"""
        all_cookware = []
        for step in self.steps:
            all_cookware.extend(step.cookware)
        return self._deduplicate_cookware(all_cookware)

    @property
    def timers(self) -> List[Timer]:
        """Get all unique timers from all steps"""
        all_timers = []
        for step in self.steps:
            all_timers.extend(step.timers)
        return self._deduplicate_timers(all_timers)

    def to_cooklang(self) -> str:
        """Convert back to Cooklang format"""
        result = []

        # Add metadata
        if self.metadata:
            result.append("---")
            result.append(yaml.dump(self.metadata, default_flow_style=False).strip())
            result.append("---")
            result.append("")

        # Add sections and steps
        current_section = None
        for step in self.steps:
            if step.section and step.section != current_section:
                current_section = step.section
                section_markers = "=" * current_section.level
                result.append(
                    f"{section_markers} {current_section.title} {section_markers}"
                )
                result.append("")

            result.append(step.to_cooklang())
            result.append("")

        return "\n".join(result).strip()

    def to_markdown(
        self,
        include_ingredients: bool = True,
        include_cookware: bool = True,
        include_instructions: bool = True,
    ) -> str:
        """Convert to Markdown format"""
        result = []

        # Add title
        if self.title:
            result.append(f"# {self.title}")
            result.append("")

        # Add ingredients
        if self.ingredients and include_ingredients:
            result.append("## Ingredients")
            result.append("")
            for ingredient in self.ingredients:
                result.append(f"- {ingredient}")
            result.append("")

        # Add cookware
        if self.cookware and include_cookware:
            result.append("## Equipment")
            result.append("")
            for cookware in self.cookware:
                result.append(f"- {cookware}")
            result.append("")

        # Add sections and steps
        if self.steps and include_instructions:
            result.append("## Instructions")
            result.append("")

            current_section = None

            for step in self.steps:
                if step.section and step.section != current_section:
                    current_section = step.section
                    section_level = min(current_section.level + 2, 6)  # Max h6
                    section_markers = "#" * section_level
                    result.append(f"{section_markers} {current_section.title}")
                    result.append("")

                result.append(f"{step.to_markdown()}")
                result.append("")

        return "\n".join(result).strip()

    def to_latex(self) -> str:
        """
        Converts to latex cookbook format
        """
        raise NotImplementedError("LaTeX export not implemented yet")

    def to_html(self, image_path: Path | None) -> str:
        """
        Converts to HTML format
        """
        results = []

        # Add title
        if self.title:
            results.append(f"<h1>{self.title}</h1>")

        if self.metadata.get("image") or image_path:
            results.append(
                f'<img src="{self.metadata["image"] if not image_path else image_path}" alt="Recipe Image for {self.title or "Recipe"}"/>'
            )

        # Add Ingredients
        if self.ingredients:
            results.append("<h2>Ingredients</h2>")
            results.append("<ul>")
            for ingredient in self.ingredients:
                results.append(f"<li>{ingredient}</li>")
            results.append("</ul>")
        # Add Cookware
        if self.cookware:
            results.append("<h2>Equipment</h2>")
            results.append("<ul>")
            for cookware in self.cookware:
                results.append(f"<li>{cookware}</li>")
            results.append("</ul>")
        # Add Instructions
        if self.steps:
            results.append("<h2>Instructions</h2>")
            for step in self.steps:
                results.append(f"<p>{step.to_html()}</p>")
        return "\n".join(results).strip()

    def to_text(self) -> str:
        """Convert to plain text format"""
        results = []
        if self.title:
            results.append(self.title)
            results.append("")

        for step in self.steps:
            results.append(step.to_plain_text())
            results.append("")

        return "\n".join(results).strip()

    def _deduplicate_ingredients(
        self, ingredients: List[Ingredient]
    ) -> List[Ingredient]:
        """Remove duplicate ingredients while preserving order"""
        seen = set()
        result = []
        for ingredient in ingredients:
            key = (
                ingredient.name,
                ingredient.unit,
                ingredient.preparation,
                ingredient.quantity,
            )
            if key not in seen:
                seen.add(key)
                result.append(ingredient)
        return result

    def _deduplicate_cookware(self, cookware: List[Cookware]) -> List[Cookware]:
        """Remove duplicate cookware while preserving order"""
        seen = set()
        result = []
        for item in cookware:
            if item.name not in seen:
                seen.add(item.name)
                result.append(item)
        return result

    def _deduplicate_timers(self, timers: List[Timer]) -> List[Timer]:
        """Remove duplicate timers while preserving order"""
        seen = set()
        result = []
        for timer in timers:
            key = (timer.name, timer.duration, timer.unit)
            if key not in seen:
                seen.add(key)
                result.append(timer)
        return result


def parse_number(value: str, fractions: bool = False) -> Union[int, float, str]:
    try:
        if fractions and "/" in value:
            num, denom = value.split("/", 1)
            return float(num) / float(denom)
        return float(value) if "." in value else int(value)
    except Exception:
        return value


class CooklangParser:
    """
    Self-contained parser for Cooklang recipe markup language.

    Usage:
        parser = CooklangParser()
        recipe = parser.parse(cooklang_text)
    """

    def __init__(self):
        self.setup_regex()

    def _get_matching_regex(
        self, qualifier: str, required_name: bool = True
    ) -> re.Pattern:
        regex_pattern = r"(?:"
        regex_pattern += re.escape(qualifier)
        regex_pattern += r"(?P<name>[\w\s()\\/\\-]"
        regex_pattern += r"+" if required_name else r"*"
        regex_pattern += r"){(?P<amount>[\d.\/\-]+)?%*(?P<unit>[A-Za-z]+)?}(?:\((?P<shorthand>[\w\s]+)\))?)|(?:"
        regex_pattern += re.escape(qualifier)
        regex_pattern += r"(?P<simple>\w+))"

        return re.compile(regex_pattern)

    def setup_regex(self):
        self.ingredient_pattern = self._get_matching_regex(r"@")
        self.cookware_pattern = self._get_matching_regex(r"#")
        self.timer_pattern = self._get_matching_regex(r"~", required_name=False)

        self.comment_inline_pattern = re.compile(r"--(.*)$", re.MULTILINE)
        self.comment_block_pattern = re.compile(r"\[-\s*(.*?)\s*-\]", re.DOTALL)
        self.note_pattern = re.compile(r"^>\s*(.*)$", re.MULTILINE)
        self.section_pattern = re.compile(r"^(=+)\s*(.*?)\s*(=*)$")

    def parse(self, text: str) -> Recipe:
        """Parse Cooklang text and return a Recipe object"""
        recipe = Recipe()

        # Extract and parse metadata (YAML front matter)
        text, recipe.metadata = self._parse_metadata(text)

        # Set title from metadata if available
        recipe.title = recipe.metadata.get("title")

        # Split text into paragraphs (steps are separated by empty lines)
        paragraphs = self._split_into_paragraphs(text)

        current_section = None

        for paragraph in paragraphs:
            paragraph = paragraph.strip()
            if not paragraph:
                continue

            # Check for section headers
            section_match = self.section_pattern.match(paragraph)
            if section_match:
                level = len(section_match.group(1))
                title = section_match.group(2).strip()
                current_section = Section(title=title, level=level)
                recipe.sections.append(current_section)
                continue

            # Parse the paragraph as a step
            step = self._parse_step(paragraph)
            step.section = current_section
            recipe.steps.append(step)

        # Ingredients, cookware, and timers are now automatically available as properties
        return recipe

    def _parse_metadata(self, text: str) -> Tuple[str, Dict]:
        """Extract and parse YAML front matter - improved version"""
        lines = text.split("\n")
        if lines and lines[0].strip() == "---":
            try:
                # Find the closing ---
                end_idx = None
                for i, line in enumerate(lines[1:], 1):
                    if line.strip() == "---":
                        end_idx = i
                        break

                if end_idx:
                    yaml_content = "\n".join(lines[1:end_idx])
                    metadata = yaml.safe_load(yaml_content) or {}
                    remaining_text = "\n".join(lines[end_idx + 1 :]).strip()
                    return remaining_text, metadata
            except yaml.YAMLError:
                pass

        return text, {}

    def _split_into_paragraphs(self, text: str) -> List[str]:
        """Split text into paragraphs (separated by empty lines)"""
        # Split on double newlines or more
        paragraphs = re.split(r"\n\s*\n", text.strip())
        return [p.strip() for p in paragraphs if p.strip()]

    def _parse_step(self, text: str) -> Step:
        """Parse a single step into a sequence of tokens"""
        tokens = []
        position = 0

        # Find all matches for different token types
        all_matches = []

        # Find ingredients
        for match in self.ingredient_pattern.finditer(text):
            ingredient = self._create_ingredient_from_match(match)
            all_matches.append((match.start(), match.end(), ingredient, match.group(0)))

        # Find cookware
        for match in self.cookware_pattern.finditer(text):
            cookware = self._create_cookware_from_match(match)
            all_matches.append((match.start(), match.end(), cookware, match.group(0)))

        # Find timers
        for match in self.timer_pattern.finditer(text):
            timer = self._create_timer_from_match(match)
            all_matches.append((match.start(), match.end(), timer, match.group(0)))

        # Find notes
        for match in self.note_pattern.finditer(text):
            note = Note(text=match.group(1).strip())
            all_matches.append((match.start(), match.end(), note, match.group(0)))

        # Find inline comments
        for match in self.comment_inline_pattern.finditer(text):
            comment = Comment(text=match.group(1).strip(), is_block=False)
            all_matches.append((match.start(), match.end(), comment, match.group(0)))

        # Find block comments
        for match in self.comment_block_pattern.finditer(text):
            comment = Comment(text=match.group(1).strip(), is_block=True)
            all_matches.append((match.start(), match.end(), comment, match.group(0)))

        # Sort matches by position
        all_matches.sort(key=lambda x: x[0])

        # Build tokens, filling gaps with text tokens
        for start, end, data, original_text in all_matches:
            # Add text token for any gap before this match
            if position < start:
                gap_text = text[position:start]
                if gap_text.strip():  # Only add non-whitespace text
                    tokens.append(
                        TextToken(text=gap_text, start_pos=position, end_pos=start)
                    )

            # Add the specific token
            if isinstance(data, Ingredient):
                tokens.append(
                    IngredientToken(
                        text=original_text,
                        start_pos=start,
                        end_pos=end,
                        ingredient=data,
                    )
                )
            elif isinstance(data, Cookware):
                tokens.append(
                    CookwareToken(
                        text=original_text, start_pos=start, end_pos=end, cookware=data
                    )
                )
            elif isinstance(data, Timer):
                tokens.append(
                    TimerToken(
                        text=original_text, start_pos=start, end_pos=end, timer=data
                    )
                )
            elif isinstance(data, Comment):
                tokens.append(
                    CommentToken(
                        text=original_text, start_pos=start, end_pos=end, comment=data
                    )
                )
            elif isinstance(data, Note):
                tokens.append(
                    NoteToken(
                        text=original_text, start_pos=start, end_pos=end, note=data
                    )
                )
            else:
                raise ValueError("Unknown data type in token parsing")
            position = end

        # Add any remaining text
        if position < len(text):
            remaining_text = text[position:]
            if remaining_text.strip():
                tokens.append(
                    TextToken(
                        text=remaining_text, start_pos=position, end_pos=len(text)
                    )
                )
        return Step(tokens=tokens)

    def _create_ingredient_from_match(self, match) -> Ingredient:
        """Create an Ingredient object from a regex match"""
        if match.group("simple"):
            return Ingredient(name=match.group("simple").strip())

        name = match.group("name").strip()

        quantity_str = match.group("amount") if match.group("amount") else None
        unit = match.group("unit") if match.group("unit") else None
        # Handle both preparation syntaxes
        preparation = match.group("shorthand")
        quantity = None
        if quantity_str:
            quantity = parse_number(quantity_str)

        return Ingredient(
            name=name, quantity=quantity, unit=unit, preparation=preparation
        )

    def _create_cookware_from_match(self, match) -> Cookware:
        """Create a Cookware object from a regex match"""
        if match.group("simple"):
            return Cookware(name=match.group("simple").strip())
        name = match.group("name").strip()
        quantity = match.group("amount") if match.group("amount") else None
        return Cookware(name=name, quantity=quantity)

    def _create_timer_from_match(self, match) -> Timer:
        """Create a Timer object from a regex match"""
        if match.group("simple"):
            raise ValueError("Timer must have a duration")
        name = match.group("name").strip() if match.group("name") else None
        duration_str = match.group("amount") if match.group("amount") else None
        unit = match.group("unit") if match.group("unit") else None

        duration = None
        if duration_str:
            duration = parse_number(duration_str)

        return Timer(name=name, duration=duration, unit=unit)


def find_related_image(file_path: str | Path) -> Optional[Path]:
    """
    Given a Cooklang file path, look for an image with the same base name
    and common image extensions in the same directory.

    Args:
        file_path: Path to the Cooklang file
    Returns:
        Path to the related image if found, else None
    """
    if isinstance(file_path, str):
        file_path = Path(file_path)

    image_extensions = [".webp", ".jpg", ".jpeg", ".png", ".bmp", ".gif", ".heic"]
    base_name = file_path.stem
    directory = file_path.parent

    for ext in image_extensions:
        candidate = directory / f"{base_name}{ext}"
        if candidate.exists():
            return candidate

    return None


def read_cook(
    file_path: str | Path, infer_title: bool = True, search_image: bool = True
) -> Recipe:
    """
    Read a Cooklang file and parse it into a Recipe object

    Args:
        file_path: Path to the Cooklang file
        infer_title: If True, infer title from filename if not in metadata
    Returns:
        Recipe object parsed from the file
    """
    if isinstance(file_path, str):
        file_path = Path(file_path)

    if not file_path.exists():
        raise FileNotFoundError(f"Cooklang not found: {file_path}")

    text = file_path.read_text(encoding="utf-8")
    parser = CooklangParser()
    try:
        recipe = parser.parse(text)
    except Exception as e:
        raise ValueError(f"Error parsing Cooklang file: {e}")

    if infer_title and not recipe.title:
        recipe.title = file_path.stem.replace("_", " ").replace("-", " ").title()

    if search_image:
        image_path = find_related_image(file_path)
        if image_path:
            recipe.metadata["image"] = str(image_path)

    return recipe
