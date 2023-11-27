# Generated from mal.g4 by ANTLR 4.13.1
from antlr4 import *
if "." in __name__:
    from .malParser import malParser
else:
    from malParser import malParser

# This class defines a complete generic visitor for a parse tree produced by malParser.

class malVisitor(ParseTreeVisitor):

    # Visit a parse tree produced by malParser#mal.
    def visitMal(self, ctx:malParser.MalContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by malParser#declaration.
    def visitDeclaration(self, ctx:malParser.DeclarationContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by malParser#include.
    def visitInclude(self, ctx:malParser.IncludeContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by malParser#define.
    def visitDefine(self, ctx:malParser.DefineContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by malParser#category.
    def visitCategory(self, ctx:malParser.CategoryContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by malParser#meta.
    def visitMeta(self, ctx:malParser.MetaContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by malParser#asset.
    def visitAsset(self, ctx:malParser.AssetContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by malParser#step.
    def visitStep(self, ctx:malParser.StepContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by malParser#steptype.
    def visitSteptype(self, ctx:malParser.SteptypeContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by malParser#tag.
    def visitTag(self, ctx:malParser.TagContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by malParser#cias.
    def visitCias(self, ctx:malParser.CiasContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by malParser#cia.
    def visitCia(self, ctx:malParser.CiaContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by malParser#ttc.
    def visitTtc(self, ctx:malParser.TtcContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by malParser#ttcexpr.
    def visitTtcexpr(self, ctx:malParser.TtcexprContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by malParser#ttcterm.
    def visitTtcterm(self, ctx:malParser.TtctermContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by malParser#ttcfact.
    def visitTtcfact(self, ctx:malParser.TtcfactContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by malParser#ttcatom.
    def visitTtcatom(self, ctx:malParser.TtcatomContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by malParser#ttcdist.
    def visitTtcdist(self, ctx:malParser.TtcdistContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by malParser#precondition.
    def visitPrecondition(self, ctx:malParser.PreconditionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by malParser#reaches.
    def visitReaches(self, ctx:malParser.ReachesContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by malParser#number.
    def visitNumber(self, ctx:malParser.NumberContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by malParser#variable.
    def visitVariable(self, ctx:malParser.VariableContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by malParser#expr.
    def visitExpr(self, ctx:malParser.ExprContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by malParser#parts.
    def visitParts(self, ctx:malParser.PartsContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by malParser#part.
    def visitPart(self, ctx:malParser.PartContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by malParser#varsubst.
    def visitVarsubst(self, ctx:malParser.VarsubstContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by malParser#type.
    def visitType(self, ctx:malParser.TypeContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by malParser#setop.
    def visitSetop(self, ctx:malParser.SetopContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by malParser#associations.
    def visitAssociations(self, ctx:malParser.AssociationsContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by malParser#association.
    def visitAssociation(self, ctx:malParser.AssociationContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by malParser#field.
    def visitField(self, ctx:malParser.FieldContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by malParser#mult.
    def visitMult(self, ctx:malParser.MultContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by malParser#multatom.
    def visitMultatom(self, ctx:malParser.MultatomContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by malParser#linkname.
    def visitLinkname(self, ctx:malParser.LinknameContext):
        return self.visitChildren(ctx)



del malParser