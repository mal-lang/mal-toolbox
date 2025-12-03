# MAL Grammar and Parser Generation

This project uses ANTLR to define the MAL language grammar and generate the Python parser and lexer. This README explains how to update the grammar and regenerate the parser/lexer.

---


## Prerequisites

Install python runtime for ANTLR:
`pip install antlr4-python3-runtime`

## Updating the Grammar

Edit the grammar file mal.g4 in this directory.

Make sure you follow ANTLR 4 syntax.

Add or modify rules as needed, but be careful to maintain backward compatibility if your existing MAL files must still parse correctly.

## Generating Parser and Lexer

`antlr4 -Dlanguage=Python3 mal.g4 -visitor -no-listener`

Copy content from malParser.py and malLexer.py to mal_parser.py and mal_lexer.py.

## Run formatting

Add `#fmt: off` and `#fmt: on` around the generated function `serializedATN` in both the parser and the lexer to avoid formatting those lines.
Run `ruff format <files>` to format the files. This makes it more simple to see changes.

