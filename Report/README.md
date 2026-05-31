# Report (LaTeX)

This folder contains a complete jury-defense report for the EcoEye2 project.

## Contents

- `main.tex`: full report manuscript (20+ pages target when compiled)
- `references.bib`: bibliography file

## Build Instructions

From this folder:

```bash
pdflatex main.tex
bibtex main
pdflatex main.tex
pdflatex main.tex
```

If your LaTeX distribution supports `latexmk`:

```bash
latexmk -pdf main.tex
```

Output file: `main.pdf`.

## Customization Before Defense

Edit placeholders in the title page:

- student name
- supervisor
- jury members
- university/faculty names

You can also adapt chapter text to your institution format (language, required sections, annexes).
