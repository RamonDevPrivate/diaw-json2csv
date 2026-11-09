# diaw-json2csv

Converts a JSON export of the Quarto question catalogue into a CSV file for import into the evaexam question library.

Every question becomes a single choice question: the correct answer (`schluessel`) scores 1 point, each distractor 0 points. evaexam shuffles the answers itself when it creates variants of an exam. The question group in evaexam is the question's `abschnitt`. Question text and answers are passed on as HTML, joined onto one line. The catalogue id ends up in the evaexam field "Kurzname".

## Usage

Needs only Python 3.12 or newer, no other packages:

```sh
python3 json2csv.py kap1-lernfragen.json                 # writes kap1-lernfragen.csv
python3 json2csv.py questions.json -o import.csv
python3 json2csv.py questions.json --status freigegeben  # only approved questions
python3 json2csv.py questions.json --status freigegeben --status review
python3 json2csv.py questions.json --encoding cp1252     # if evaexam shows broken umlauts
python3 json2csv.py questions.json --delimiter ,         # if evaexam expects another delimiter
```

Every question needs a correct answer and at least two distractors; no answer may be empty, duplicated or contain `|`. If any question has a problem, the program lists all problems and writes no file.

Development with [uv](https://docs.astral.sh/uv/):

```sh
uv run ruff format .     # format code
uv run ruff check .      # lint
uv run basedpyright      # type check
uv run pytest            # tests
```

## License

[MIT](LICENSE)
