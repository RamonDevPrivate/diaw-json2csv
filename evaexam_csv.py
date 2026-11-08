"""Convert a JSON export of the Quarto question catalogue into an evaexam CSV file.

The CSV layout follows the evaexam manual, section "Im- und Export der Fragenbibliothek"
(columns A-O, no header row). Every question becomes a single choice question with the
key (correct answer) first; evaexam shuffles the options itself when it builds variants.
"""

import argparse
import csv
import io
import json
import sys
from collections import Counter
from collections.abc import Mapping
from pathlib import Path
from typing import TypedDict, cast

SINGLE_CHOICE = 10  # column B: question type
SEPARATOR = "|"  # separates options (column E) and points (column H)
STATUSES = ("entwurf", "review", "freigegeben", "gesperrt")  # status values of the catalogue


class Question(TypedDict):
    """One question of the JSON export; field names come from the catalogue."""

    id: str
    status: str
    abschnitt: str
    stamm: str
    schluessel: str
    distraktoren: list[str]
    begruendung: str


TEXT_FIELDS = sorted(Question.__required_keys__ - {"distraktoren"})


def one_line(html: str) -> str:
    """Join the lines of an HTML fragment: line breaks don't matter in HTML, but may in CSV."""
    return " ".join(html.splitlines()).strip()


def answers(question: Question) -> list[str]:
    """Return all options on one line each, the correct one first."""
    return [one_line(a) for a in [question["schluessel"], *question["distraktoren"]]]


def is_list_of(value: object, kind: type) -> bool:
    """Return True if value is a list whose items are all of the given type."""
    return isinstance(value, list) and all(isinstance(v, kind) for v in cast("list[object]", value))


def problems(question: Mapping[str, object]) -> list[str]:
    """Return what prevents this question from being imported (empty if nothing)."""
    invalid = [key for key in TEXT_FIELDS if not isinstance(question.get(key), str)]
    if not is_list_of(question.get("distraktoren"), str):
        invalid.append("distraktoren")
    if invalid:
        return [f"missing or invalid fields: {', '.join(invalid)}"]
    valid = cast("Question", question)
    options = answers(valid)
    found: list[str] = []
    if len(options) < 3:
        found.append("at least two distractors needed")
    if not valid["stamm"].strip() or not all(options):
        found.append("empty question text or answer")
    if any(SEPARATOR in option for option in options):
        found.append(f"an answer contains {SEPARATOR!r}, which evaexam uses as separator")
    if len(set(options)) < len(options):
        found.append("duplicate answers")
    return found


def to_row(question: Question) -> list[str | int]:
    """Map a question to the columns A-O of the evaexam question library CSV."""
    options = answers(question)
    points = [1] + [0] * (len(options) - 1)
    return [
        question["abschnitt"],  # A question group
        SINGLE_CHOICE,  # B question type
        len(options),  # C number of options
        one_line(question["stamm"]),  # D question text
        SEPARATOR.join(options),  # E options
        "",  # F unused, but must be present
        "",  # G only used by matching questions
        SEPARATOR.join(map(str, points)),  # H points per option, same order as E
        1,  # I exam question (0 would be a course evaluation question)
        0,  # J no difficulty assigned
        "",  # K max. characters, only for open questions
        "",  # L extra flags, none for plain single choice
        question["id"],  # M short name, unused by evaexam; links back to the catalogue
        one_line(question["begruendung"]),  # N explanation
        "",  # O reference
    ]


def load(path: Path) -> list[dict[str, object]]:
    """Read the JSON export; the fields of each question are checked later by problems()."""
    try:
        data: object = json.loads(path.read_text(encoding="utf-8"))  # pyright: ignore[reportAny]
    except json.JSONDecodeError as error:
        raise ValueError(f"{path}: invalid JSON ({error})") from error
    if not is_list_of(data, dict):
        raise ValueError(f"{path}: expected a JSON list of questions (objects)")
    return cast("list[dict[str, object]]", data)


def delimiter(value: str) -> str:
    """Accept a single character that cannot be confused with the CSV content."""
    if len(value) != 1 or value in f'{SEPARATOR}"\r\n':
        raise argparse.ArgumentTypeError(f'expected a single character other than {SEPARATOR} and "')
    return value


class Options(argparse.Namespace):
    """Typed command line options."""

    json_file: Path
    output: Path | None
    status: list[str] | None
    delimiter: str
    encoding: str


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Convert a JSON export of the question catalogue into an evaexam CSV.")
    parser.add_argument("json_file", type=Path, help="JSON export of the question catalogue")
    parser.add_argument("-o", "--output", type=Path, help="CSV file")
    parser.add_argument(
        "--status",
        action="append",
        choices=STATUSES,
        help="only export questions with this status; repeatable (default: all)",
    )
    parser.add_argument("--delimiter", type=delimiter, default=";", help="default: ;")
    parser.add_argument("--encoding", default="utf-8", help="default: utf-8")
    args = parser.parse_args(argv, namespace=Options())
    target = args.output or args.json_file.with_suffix(".csv")

    try:
        if target.resolve() == args.json_file.resolve():
            raise ValueError(f"{target}: output would overwrite the input")
        questions = load(args.json_file)
        selected = [q for q in questions if args.status is None or q.get("status") in args.status]
        errors = [f"{q.get('id', '?')}: {p}" for q in selected for p in problems(q)]
        if errors:
            raise ValueError("\n".join(errors))
        if not selected:
            raise ValueError("no questions selected, no CSV written")
        valid = cast("list[Question]", selected)
        buffer = io.StringIO()
        csv.writer(buffer, delimiter=args.delimiter).writerows(to_row(q) for q in valid)
        target.write_bytes(buffer.getvalue().encode(args.encoding))
    except (OSError, ValueError, LookupError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1

    by_status = Counter(q["status"] for q in valid)
    summary = ", ".join(f"{status}: {n}" for status, n in sorted(by_status.items()))
    skipped = len(questions) - len(selected)
    print(f"{len(selected)} exported ({summary}), {skipped} skipped -> {target}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
