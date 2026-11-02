"""Render all course outputs in one go.

    resources/   the course pages
        hpc-ai-notes.html           instructor notes (includes "Instructor notes" boxes)
        hpc-ai-notes-attendee.html  attendee notes (instructor boxes removed)
        hpc-ai-slides.html          revealjs slides
    docs/        the course website for GitHub Pages
        index.html       attendee notes with the slides embedded at the top
        slides.html      copy of resources/hpc-ai-slides.html
        instructor.html  copy of resources/hpc-ai-notes.html

Run from this folder with:

    python render.py

Needs Quarto (https://quarto.org) and Python 3.9 or later. No Python packages
are needed: the notes show the course code but don't run it.
"""

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "source"
NOTES = "hpc-ai-notes.qmd"
SLIDES = "hpc-ai-slides.qmd"
NOTEBOOK = ROOT / "notebooks" / "hpc-for-ai.ipynb"


def render_to(input_file, output, metadata=None):
    """Render a .qmd in source/ and move the result to `output`.

    Quarto writes each output next to its .qmd, so we render there and then
    move the file to where it belongs.
    """
    output = ROOT / output
    cmd = ["quarto", "render", input_file, "--output", output.name]
    for key, value in (metadata or {}).items():
        cmd += ["-M", f"{key}:{value}"]
    subprocess.run(cmd, cwd=SOURCE, check=True)
    output.unlink(missing_ok=True)
    shutil.move(SOURCE / output.name, output)


def check_notebook_matches_notes():
    """Every notebook code block in the notes must match a cell in the notebook.

    Code blocks headed `filename="hpc-for-ai.ipynb"` in the notes are copies of
    notebook cells. If you edit one, edit the other too.
    """
    notes = (SOURCE / NOTES).read_text()
    blocks = re.findall(
        r'```\{\.python filename="hpc-for-ai\.ipynb"\}\n(.*?)\n```', notes, flags=re.S
    )
    cells = {
        "".join(cell["source"]).strip()
        for cell in json.loads(NOTEBOOK.read_text())["cells"]
        if cell["cell_type"] == "code"
    }
    missing = [block for block in blocks if block.strip() not in cells]
    if missing:
        print("\nThese code blocks in the notes don't match any cell in the notebook:\n")
        for block in missing:
            print("    " + block.splitlines()[0] + " ...")
        sys.exit("Update notebooks/hpc-for-ai.ipynb or source/" + NOTES + " so they match.")
    print(f"Notebook check: all {len(blocks)} code blocks in the notes match the notebook.")


def main():
    if not (SOURCE / NOTES).exists():
        sys.exit("Please run render.py from the top-level course folder.")
    if shutil.which("quarto") is None:
        sys.exit("Quarto not found. Install it from https://quarto.org/docs/get-started/")

    check_notebook_matches_notes()

    (ROOT / "resources").mkdir(exist_ok=True)
    (ROOT / "docs").mkdir(exist_ok=True)

    print("Rendering instructor notes...")
    render_to(NOTES, "resources/hpc-ai-notes.html")

    print("Rendering attendee notes...")
    render_to(NOTES, "resources/hpc-ai-notes-attendee.html", {"attendee": "true"})

    print("Rendering slides...")
    render_to(SLIDES, "resources/hpc-ai-slides.html")

    print("Rendering course website...")
    render_to(NOTES, "docs/index.html", {"attendee": "true", "site": "true"})
    shutil.copy(ROOT / "resources/hpc-ai-slides.html", ROOT / "docs/slides.html")
    shutil.copy(ROOT / "resources/hpc-ai-notes.html", ROOT / "docs/instructor.html")
    (ROOT / "docs/.nojekyll").touch()  # serve the files as they are, no Jekyll processing

    # Safety check: the attendee copies must not contain any instructor notes
    for f in ["resources/hpc-ai-notes-attendee.html", "docs/index.html"]:
        if "Instructor notes" in (ROOT / f).read_text():
            sys.exit(
                f"{f} still contains instructor notes - check that every instructor "
                'block is wrapped in ::: {.content-hidden when-meta="attendee"}'
            )

    print("\nDone! Created:")
    for f in [
        "resources/hpc-ai-notes.html",
        "resources/hpc-ai-notes-attendee.html",
        "resources/hpc-ai-slides.html",
        "docs/index.html",
        "docs/slides.html",
        "docs/instructor.html",
    ]:
        print(f"  {f}")


if __name__ == "__main__":
    main()
