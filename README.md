This package aims to make the process of writing and editing long-form
natural-language prose, e.g. novels, more similar to standard processes for
developing software. To this end, it provides two core functions:

1. Formatting of source documents to facilitate VCS integration.

2. Converting the source documents to LaTex and rendering a PDF for a portable
and aesthetically pleasing preview.

Source documents are stored as simple text files (`.txt` format). A project can
consist of many such documents, e.g., one per chapter.

# 0. Installation

To install `prosepreview`, run
```
pip3 install git+https://github.com/noah-aviel-dove/prosepreview
```

## 0.1 Dependencies

 - [python >= 3.11.1](https://www.python.org/downloads/)
 - [jq](https://stedolan.github.io/jq/)
 - [make](https://www.gnu.org/software/make/) - Optional
 - [pandoc](https://pandoc.org/) - Optional (for importing existing documents)
 - [pdflatex](https://linux.die.net/man/1/pdflatex) - Optional (for rendering to PDF)

# 1. Setup

## 1.1 Initialization

To use `prosepreview` for a writing project, run

```
python3 -m prosepreview init
```

in the directory where you plan on storing your source documents. This will
create a subdirectory called `prosepreview` that contains the configuration for
the project, as well as a makefile that streamlines some common operations.

## 1.2 Configuration

Project configuration is stored in `prosepreview/config.json`. To start using
`prosepreview`, edit this file and populate the `sources` property with the
relative paths of the source documents. An example is provided in the initial
configuration.

### 1.2.1 Git configuration

If using `git` for your project, add the following entries to your `.gitignore`
file:

```
!prosepreview/config.json
prosepreview/*
```

## 1.3 Importing existing documents

Existing documents that are not in `.txt` format must be converted before they
can be used with `prosepreview`. [pandoc](https://pandoc.org/) may be useful for
this step.

# 2. Usage

## 2.1 Formatting source documents

For effective VCS integration, only extremely minimal embellishment of the
source documents' text is supported. The only support for formatting is that
text in \_underscores\_ is rendered in the preview in _italics_. There is no
explicit support for any other form of decoration, but most inline LaTeX should
be passed through to the compiler unchanged.

The formatter enforces line-wrapping at a configurable number of characters,
consolidation of contiguous whitespace, and line breaks at sentence boundaries
and around quotation marks. This is intended to have the net effect of having
the prose behave more like computer source code, with the following benefits:

- Improved editing performance when using line-based text editors such as `vim`.
- Expressive and efficient representation of changes in the text, making VCS
software such as `git` viable for tracking and comparing revisions.

To format all source files defined in the configuration, run

```
make -C prosepreview format
```

from the project's source directory.

To format an individual source document, run

```
python3 -m prosepreview format <source_doc.txt>
```

## 2.2 Compiling source documents

The source document format is efficient for revision control, but tedious to
read in large volumes. To facilitate a more aesthetically satisfying preview,
`prosepreview` can compile the source documents to a single
[LaTeX](https://www.latex-project.org/) file. If
[pdflatex](https://linux.die.net/man/1/pdflatex) is installed, this file can
then be rendered as a PDF. An optional watermark and page header can be
configured via `config.json`. If a local git repository has been set up for the
project, the hash of the current commit will be included in the preview.

To render the source documents as a PDF, run

```
make -C prosepreview compile
```

from the project's source directory.

To compile the source documents to LaTeX without rendering, run

```
python3 -m prosepreview compile <output.tex>
```
