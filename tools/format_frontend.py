"""Format hand-written CSS/JavaScript; use djlint separately for Jinja templates."""

from pathlib import Path

import cssbeautifier
import jsbeautifier

ROOT = Path(__file__).resolve().parent.parent
STATIC = ROOT / "mealboy" / "static"

for path in STATIC.glob("*.css"):
    formatted = cssbeautifier.beautify(path.read_text(encoding="utf-8"), {"indent_size": 2})
    path.write_text(formatted + "\n", encoding="utf-8")

for path in STATIC.glob("*.js"):
    formatted = jsbeautifier.beautify(path.read_text(encoding="utf-8"), {"indent_size": 2})
    path.write_text(formatted + "\n", encoding="utf-8")
