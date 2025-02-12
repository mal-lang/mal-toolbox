# mypy: ignore-errors
import sys
from collections.abc import MutableMapping, MutableSequence
from pathlib import Path

from antlr4 import FileStream, CommonTokenStream, ParseTreeVisitor
from antlr4.error.ErrorListener import ConsoleErrorListener

from .mal_lexer import malLexer
from .mal_parser import malParser

# In a rule like `rule: one? two* three`:
#   - ctx.one() would be None if the token was not found on a matching line
#   - ctx.two() would be []


def patched_antrl_syntax_error(self, recognizer, offendingSymbol, line, column, msg, e):
    file = patched_antrl_syntax_error.file
    print(f"{file}:{str(line)}:{str(column)}: {msg}", file=sys.stderr)


ConsoleErrorListener.syntaxError = patched_antrl_syntax_error


class MalCompiler(ParseTreeVisitor):
    def __init__(self, *args, **kwargs):
        self.current_file: Path = None
        self.visited_files: set[Path] = set()
        self.path_stack: list[Path] = []

        super().__init__(*args, **kwargs)

    def compile(self, malfile: Path | str):
        current_file = Path(malfile)

        if not current_file.is_absolute() and self.path_stack:
            # Only for the first file self.path_stack will be empty.
            current_file = self.path_stack[-1] / current_file

        if current_file in self.visited_files:
            # Avoid infinite loops due to recursive includes
            return {}

        self.visited_files.add(current_file)
        self.path_stack.append(current_file.parent)

        patched_antrl_syntax_error.file = current_file.relative_to(self.path_stack[0])

        input_stream = FileStream(current_file, encoding="utf-8")
        lexer = malLexer(input_stream)
        stream = CommonTokenStream(lexer)
        parser = malParser(stream)
        tree = parser.mal()

        result = self.visit(tree)

        self.path_stack.pop()

        return result

    def visitMal(self, ctx):
        langspec = {
            "formatVersion": "1.0.0",
            "defines": {},
            "categories": [],
            "assets": [],
            "associations": [],
        }

        # no visitDeclaration method needed, `declaration` is a thin rule
        for declaration in (d.getChild(0) for d in ctx.declaration()):
            if result := self.visit(declaration) or True:
                key, value = result

                if key == "categories":
                    category, assets = value
                    langspec["categories"].extend(category)
                    langspec["assets"].extend(assets)
                    continue

                if key == "defines":
                    langspec[key].update(value)

                if key == "associations":
                    langspec[key].extend(value)

                if key == "include":
                    included_file = self.compile(value)
                    for k, v in langspec.items():
                        if isinstance(v, MutableMapping):
                            langspec[k].update(included_file.get(k, {}))
                        if isinstance(v, MutableSequence) and k in included_file:
                            langspec[k].extend(included_file[k])

        for key in ("categories", "assets", "associations"):
            unique = []
            for item in langspec[key]:
                if item not in unique:
                    unique.append(item)
            langspec[key] = unique

        return langspec

    def visitInclude(self, ctx):
        return ("include", ctx.STRING().getText().strip('"'))

    def visitDefine(self, ctx):
        return ("defines", {ctx.ID().getText(): ctx.STRING().getText().strip('"')})

    def visitDetector(self, ctx):
        detector = {}
        detector["name"] = (
            self.visit(ctx.detectorname()) if ctx.detectorname() else None
        )
        detector["context"] = self.visit(ctx.context()) if ctx.context() else None
        detector["type"] = (
            self.visit(ctx.detectortype()) if ctx.detectortype() else None
        )
        detector["tprate"] = self.visit(ctx.tprate()) if ctx.tprate() else None

        return detector

    def visitDetectorname(self, ctx):
        return ctx.getText()

    def visitContext(self, ctx):
        return {
            # Using labels as the dict keys since multiple contextparts can
            # share the same asset type.
            # TODO: add analyzer check if two labels are same in a context
            cpart.contextlabel().getText(): cpart.contextasset().getText()
            for cpart in ctx.contextpart()
        }

    def visitDetectortype(self, ctx):
        return ctx.getText()

    def visitCategory(self, ctx):
        category = {}
        category["name"] = ctx.ID().getText()
        category["meta"] = {
            (info := self.visit(meta))[0]: info[1] for meta in ctx.meta()
        }

        assets = [self.visit(asset) for asset in ctx.asset()]

        return ("categories", ([category], assets))

    def visitMeta(self, ctx):
        return (ctx.ID().getText(), ctx.text().getText().strip("\"'"))

    def visitAsset(self, ctx):
        asset = {}
        asset["name"] = ctx.ID()[0].getText()
        asset["meta"] = {(info := self.visit(meta))[0]: info[1] for meta in ctx.meta()}
        asset["category"] = ctx.parentCtx.ID().getText()
        asset["isAbstract"] = ctx.ABSTRACT() is not None

        asset["superAsset"] = None
        if len(ctx.ID()) > 1 and ctx.ID()[1]:
            asset["superAsset"] = ctx.ID()[1].getText()

        asset["variables"] = [self.visit(variable) for variable in ctx.variable()]
        asset["attackSteps"] = [self.visit(step) for step in ctx.step()]

        return asset

    def visitStep(self, ctx):
        step = {}
        step["name"] = ctx.ID().getText()
        step["meta"] = {(info := self.visit(meta))[0]: info[1] for meta in ctx.meta()}

        # TODO: add analyzer check for conflicting detector names
        step["detectors"] = {
            (d := self.visit(detector))["name"]: d for detector in ctx.detector()
        }
        step["type"] = self.visit(ctx.steptype())
        step["tags"] = [self.visit(tag) for tag in ctx.tag()]
        step["risk"] = self.visit(ctx.cias()) if ctx.cias() else None

        # TODO: left as "ttc" for compatibility reasons
        step["ttc"] = self.visit(ctx.pdist()) if ctx.pdist() else None

        step["requires"] = (
            self.visit(ctx.precondition()) if ctx.precondition() else None
        )
        step["reaches"] = self.visit(ctx.reaches()) if ctx.reaches() else None

        return step

    def visitSteptype(self, ctx):
        return (
            "or"
            if ctx.OR()
            else "and"
            if ctx.AND()
            else "defense"
            if ctx.HASH()
            else "exist"
            if ctx.EXISTS()
            else "notExist"
            if ctx.NOTEXISTS()
            else None  # should never happen, the grammar limits it
        )

    def visitTag(self, ctx):
        return ctx.ID().getText()

    def visitCias(self, ctx):
        risk = {
            "isConfidentiality": False,
            "isIntegrity": False,
            "isAvailability": False,
        }

        for cia in ctx.cia():
            risk.update(self.visit(cia))

        return risk

    def visitCia(self, ctx):
        key = (
            "isConfidentiality"
            if ctx.C()
            else "isIntegrity"
            if ctx.I()
            else "isAvailability"
            if ctx.A()
            else None
        )

        return {key: True}

    def visitPdist(self, ctx):
        ret = self.visit(ctx.pdistexpr())

        return ret

    def visitPdistexpr(self, ctx):
        if len(terms := ctx.pdistterm()) == 1:
            return self.visit(terms[0])

        ret = {}

        lhs = self.visit(terms[0])
        for i in range(1, len(terms)):
            ret["type"] = (
                "addition"
                if ctx.children[2 * i - 1].getText() == "+"
                else "subtraction"
            )
            ret["lhs"] = lhs
            ret["rhs"] = self.visit(terms[i])

            lhs = ret.copy()

        return ret

    def visitPdistterm(self, ctx):
        if len(factors := ctx.pdistfact()) == 1:
            ret = self.visit(factors[0])
        else:
            ret = {}
            ret["type"] = "multiplication" if ctx.STAR() else "division"
            ret["lhs"] = self.visit(factors[0])
            ret["rhs"] = self.visit(factors[1])

        return ret

    def visitPdistfact(self, ctx):
        if len(atoms := ctx.pdistatom()) == 1:
            ret = self.visit(atoms[0])
        else:
            ret = {}
            ret["type"] = "exponentiation"
            ret["lhs"] = self.visit(atoms[0])
            ret["rhs"] = self.visit(atoms[1])

        return ret

    def visitPdistatom(self, ctx):
        if ctx.pdistdist():
            ret = self.visit(ctx.pdistdist())
        elif ctx.pdistexpr():
            ret = self.visit(ctx.pdistexpr())
        elif ctx.number():
            ret = self.visit(ctx.number())

        return ret

    def visitPdistdist(self, ctx):
        ret = {"type": "function"}
        ret["name"] = ctx.ID().getText()
        ret["arguments"] = []

        if ctx.LPAREN():
            ret["arguments"] = [self.visit(number)["value"] for number in ctx.number()]

        return ret

    def visitPrecondition(self, ctx):
        ret = {}
        ret["overrides"] = True
        ret["stepExpressions"] = [self.visit(expr) for expr in ctx.expr()]
        return ret

    def visitReaches(self, ctx):
        ret = {}
        ret["overrides"] = ctx.INHERITS() is None
        ret["stepExpressions"] = [self.visit(expr) for expr in ctx.expr()]

        return ret

    def visitNumber(self, ctx):
        ret = {"type": "number"}
        ret["value"] = float(ctx.getText())

        return ret

    def visitVariable(self, ctx):
        ret = {}
        ret["name"] = ctx.ID().getText()
        ret["stepExpression"] = self.visit(ctx.expr())

        return ret

    def visitExpr(self, ctx):
        if len(ctx.parts()) == 1:
            return self.visit(ctx.parts()[0])

        ret = {}
        lhs = self.visit(ctx.parts()[0])
        for i in range(1, len(ctx.parts())):
            ret["type"] = self.visit(ctx.children[2 * i - 1])
            ret["lhs"] = lhs
            ret["rhs"] = self.visit(ctx.parts()[i])
            lhs = ret.copy()

        return ret

    def visitParts(self, ctx):
        if len(ctx.part()) == 1:
            return self.visit(ctx.part()[0])

        ret = {}

        lhs = self.visit(ctx.part()[0])

        for i in range(1, len(ctx.part())):
            ret["type"] = "collect"
            ret["lhs"] = lhs
            ret["rhs"] = self.visit(ctx.part()[i])

            lhs = ret.copy()

        return ret

    def visitPart(self, ctx):
        ret = {}
        if ctx.varsubst():
            ret["type"] = "variable"
            ret["name"] = self.visit(ctx.varsubst())
        elif ctx.LPAREN():
            ret = self.visit(ctx.expr())
        else:  # ctx.ID()
            # Resolve type: field or attackStep?
            ret["type"] = self._resolve_part_ID_type(ctx)

            ret["name"] = ctx.ID().getText()

        if ctx.STAR():
            ret = {"type": "transitive", "stepExpression": ret}

        for type_ in ctx.type_():  # mind the trailing underscore
            ret = {
                "type": "subType",
                "subType": self.visit(type_),
                "stepExpression": ret,
            }

        return ret

    def _resolve_part_ID_type(self, ctx):
        pctx = ctx.parentCtx

        # Traverse up the tree until we find the parent of the topmost expr
        # (saying "topmost" as expr can be nested) or the root of the tree.
        while pctx and not isinstance(
            pctx,
            malParser.ReachesContext,
            # Expressions are also valid in `let` variable assignments, but
            # there every lexical component of expr is considered a "field",
            # no need to resolve the type in that case. Similarly, preconditions
            # (`<-`) only accept fields.
        ):
            pctx = pctx.parentCtx

        if pctx is None:
            # ctx (the `part`) belongs to a "let" assignment or a precondition.
            return "field"

        # scan for a dot to the right of `ctx`
        file_tokens = ctx.parser.getTokenStream().tokens
        for i in range(ctx.start.tokenIndex, pctx.stop.tokenIndex + 1):
            if file_tokens[i].type == malParser.DOT:
                return "field"

            # We are looping until the end of pctx (which is a `reaches` or
            # `precondition` context). This could include multiple comma
            # separated `expr`s, we only care for the current one.
            if file_tokens[i].type == malParser.COMMA:  # end of current `expr`
                return "attackStep"

        return "attackStep"

    def visitVarsubst(self, ctx):
        return ctx.ID().getText()

    def visitType(self, ctx):
        return ctx.ID().getText()

    def visitSetop(self, ctx):
        return (
            "union"
            if ctx.UNION()
            else "intersection"
            if ctx.INTERSECT()
            else "difference"
            if ctx.INTERSECT
            else None
        )

    def visitAssociations(self, ctx):
        associations = []
        for assoc in ctx.association():
            associations.append(self.visit(assoc))

        return ("associations", associations)

    def visitAssociation(self, ctx):
        association = {}

        association["name"] = self.visit(ctx.linkname())
        association["meta"] = {
            (info := self.visit(meta))[0]: info[1] for meta in ctx.meta()
        }
        association["leftAsset"] = ctx.ID()[0].getText()
        association["leftField"] = self.visit(ctx.field()[0])

        # no self.visitMult or self.visitMultatom methods, reading them here
        # directly
        association["leftMultiplicity"] = {
            "min": (multatoms := ctx.mult()[0].multatom()).pop(0).getText(),
            "max": multatoms.pop().getText() if multatoms else None,
        }
        association["rightAsset"] = ctx.ID()[1].getText()
        association["rightField"] = self.visit(ctx.field()[1])
        association["rightMultiplicity"] = {
            "min": (multatoms := ctx.mult()[1].multatom()).pop(0).getText(),
            "max": multatoms.pop().getText() if multatoms else None,
        }

        self._post_process_multitudes(association)
        return association

    def _post_process_multitudes(self, association):
        mult_keys = [
            # start the multatoms from right to left to make sure the rules
            # below get applied cleanly
            "rightMultiplicity.max",
            "rightMultiplicity.min",
            "leftMultiplicity.max",
            "leftMultiplicity.min",
        ]

        for mult_key in mult_keys:
            key, subkey = mult_key.split(".")

            # upper limit equals lower limit if not given
            if subkey == "max" and association[key][subkey] is None:
                association[key][subkey] = association[key]["min"]

            if association[key][subkey] == "*":
                # 'any' as lower limit means start from 0
                if subkey == "min":
                    association[key][subkey] = 0

                # 'any' as upper limit means not limit
                else:
                    association[key][subkey] = None

            # cast numerical strings to integers
            if (multatom := association[key][subkey]) and multatom.isdigit():
                association[key][subkey] = int(association[key][subkey])

    def visitField(self, ctx):
        return ctx.ID().getText()

    def visitLinkname(self, ctx):
        return ctx.ID().getText()
