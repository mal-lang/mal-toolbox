#!/bin/bash

set -euo pipefail

[[ ! -r antlr.jar ]] && \
  curl -qo antlr.jar 'https://www.antlr.org/download/antlr-4.13.2-complete.jar'

java -jar antlr.jar -Dlanguage=Python3 -visitor mal.g4

mv malLexer.py mal_lexer.py
mv malParser.py mal_parser.py
