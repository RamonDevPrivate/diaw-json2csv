import csv
import json
from pathlib import Path
from typing import cast

import pytest

from evaexam_csv import Question, main, problems, to_row

EXAMPLE: Question = {
    "id": "k1-0-01",
    "status": "review",
    "abschnitt": "1.4 Forschung & Entwicklung",
    "stamm": "<p>Was ist <em>richtig</em>; was nicht?</p>",
    "schluessel": "Richtig",
    "distraktoren": ["Falsch A", "Falsch B", "Falsch C"],
    "begruendung": "\n<p>Erster Absatz.</p>\n<p>Zweiter Absatz.</p>\n",
}


def make_question(**changes: object) -> Question:
    """Return a copy of EXAMPLE with fields replaced; a field set to None is removed."""
    question = {k: v for k, v in {**EXAMPLE, **changes}.items() if v is not None}
    return cast("Question", question)  # pyright: ignore[reportInvalidCast] - may be invalid on purpose


def test_to_row_maps_all_columns() -> None:
    assert to_row(EXAMPLE) == [
        "1.4 Forschung & Entwicklung",
        10,
        4,
        "<p>Was ist <em>richtig</em>; was nicht?</p>",
        "Richtig|Falsch A|Falsch B|Falsch C",
        "",
        "",
        "1|0|0|0",
        1,
        0,
        "",
        "",
        "k1-0-01",
        "<p>Erster Absatz.</p> <p>Zweiter Absatz.</p>",
        "",
    ]


@pytest.mark.parametrize(
    ("changes", "expected"),
    [
        ({}, []),
        (
            {"stamm": None, "distraktoren": "abc"},
            ["missing or invalid fields: stamm, distraktoren"],
        ),
        ({"distraktoren": ["x"]}, ["at least two distractors needed"]),
        ({"stamm": " ", "distraktoren": ["x", "", "y"]}, ["empty question text or answer"]),
        ({"schluessel": "a|b"}, ["an answer contains '|', which evaexam uses as separator"]),
        ({"distraktoren": ["Richtig", "x", "y"]}, ["duplicate answers"]),
    ],
)
def test_problems(changes: dict[str, object], expected: list[str]) -> None:
    assert problems(make_question(**changes)) == expected


def test_main_writes_selected_questions(tmp_path: Path) -> None:
    questions = [make_question(id="a", status="freigegeben"), make_question(id="b")]
    source = tmp_path / "questions.json"
    source.write_text(json.dumps(questions), encoding="utf-8")

    assert main([str(source), "--status", "freigegeben"]) == 0

    with (tmp_path / "questions.csv").open(encoding="utf-8", newline="") as file:
        rows = list(csv.reader(file, delimiter=";"))
    assert rows == [[str(value) for value in to_row(questions[0])]]


def test_main_writes_nothing_on_invalid_questions(tmp_path: Path) -> None:
    source = tmp_path / "questions.json"
    source.write_text(json.dumps([EXAMPLE, make_question(schluessel="a|b")]), encoding="utf-8")

    assert main([str(source)]) == 1

    assert not (tmp_path / "questions.csv").exists()
