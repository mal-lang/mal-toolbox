#!/usr/bin/env python


import json

from . import MalCompiler()


if __name__ == "__main__":
    compiler = MalCompiler()

    with open("new_langspec.json", "w") as f:
        json.dump(compiler.compile(sys.argv[1]), f, indent=2)
