# Generated from mal.g4 by ANTLR 4.13.1
from antlr4 import *
if "." in __name__:
    from .malParser import malParser
else:
    from malParser import malParser

# This class defines a complete listener for a parse tree produced by malParser.
class malListener(ParseTreeListener):

    # Enter a parse tree produced by malParser#mal.
    def enterMal(self, ctx:malParser.MalContext):
        pass

    # Exit a parse tree produced by malParser#mal.
    def exitMal(self, ctx:malParser.MalContext):
        pass


    # Enter a parse tree produced by malParser#declaration.
    def enterDeclaration(self, ctx:malParser.DeclarationContext):
        pass

    # Exit a parse tree produced by malParser#declaration.
    def exitDeclaration(self, ctx:malParser.DeclarationContext):
        pass


    # Enter a parse tree produced by malParser#include.
    def enterInclude(self, ctx:malParser.IncludeContext):
        pass

    # Exit a parse tree produced by malParser#include.
    def exitInclude(self, ctx:malParser.IncludeContext):
        pass


    # Enter a parse tree produced by malParser#define.
    def enterDefine(self, ctx:malParser.DefineContext):
        pass

    # Exit a parse tree produced by malParser#define.
    def exitDefine(self, ctx:malParser.DefineContext):
        pass


    # Enter a parse tree produced by malParser#category.
    def enterCategory(self, ctx:malParser.CategoryContext):
        pass

    # Exit a parse tree produced by malParser#category.
    def exitCategory(self, ctx:malParser.CategoryContext):
        pass


    # Enter a parse tree produced by malParser#meta.
    def enterMeta(self, ctx:malParser.MetaContext):
        pass

    # Exit a parse tree produced by malParser#meta.
    def exitMeta(self, ctx:malParser.MetaContext):
        pass


    # Enter a parse tree produced by malParser#asset.
    def enterAsset(self, ctx:malParser.AssetContext):
        pass

    # Exit a parse tree produced by malParser#asset.
    def exitAsset(self, ctx:malParser.AssetContext):
        pass


    # Enter a parse tree produced by malParser#step.
    def enterStep(self, ctx:malParser.StepContext):
        pass

    # Exit a parse tree produced by malParser#step.
    def exitStep(self, ctx:malParser.StepContext):
        pass


    # Enter a parse tree produced by malParser#steptype.
    def enterSteptype(self, ctx:malParser.SteptypeContext):
        pass

    # Exit a parse tree produced by malParser#steptype.
    def exitSteptype(self, ctx:malParser.SteptypeContext):
        pass


    # Enter a parse tree produced by malParser#tag.
    def enterTag(self, ctx:malParser.TagContext):
        pass

    # Exit a parse tree produced by malParser#tag.
    def exitTag(self, ctx:malParser.TagContext):
        pass


    # Enter a parse tree produced by malParser#cias.
    def enterCias(self, ctx:malParser.CiasContext):
        pass

    # Exit a parse tree produced by malParser#cias.
    def exitCias(self, ctx:malParser.CiasContext):
        pass


    # Enter a parse tree produced by malParser#cia.
    def enterCia(self, ctx:malParser.CiaContext):
        pass

    # Exit a parse tree produced by malParser#cia.
    def exitCia(self, ctx:malParser.CiaContext):
        pass


    # Enter a parse tree produced by malParser#ttc.
    def enterTtc(self, ctx:malParser.TtcContext):
        pass

    # Exit a parse tree produced by malParser#ttc.
    def exitTtc(self, ctx:malParser.TtcContext):
        pass


    # Enter a parse tree produced by malParser#ttcexpr.
    def enterTtcexpr(self, ctx:malParser.TtcexprContext):
        pass

    # Exit a parse tree produced by malParser#ttcexpr.
    def exitTtcexpr(self, ctx:malParser.TtcexprContext):
        pass


    # Enter a parse tree produced by malParser#ttcterm.
    def enterTtcterm(self, ctx:malParser.TtctermContext):
        pass

    # Exit a parse tree produced by malParser#ttcterm.
    def exitTtcterm(self, ctx:malParser.TtctermContext):
        pass


    # Enter a parse tree produced by malParser#ttcfact.
    def enterTtcfact(self, ctx:malParser.TtcfactContext):
        pass

    # Exit a parse tree produced by malParser#ttcfact.
    def exitTtcfact(self, ctx:malParser.TtcfactContext):
        pass


    # Enter a parse tree produced by malParser#ttcatom.
    def enterTtcatom(self, ctx:malParser.TtcatomContext):
        pass

    # Exit a parse tree produced by malParser#ttcatom.
    def exitTtcatom(self, ctx:malParser.TtcatomContext):
        pass


    # Enter a parse tree produced by malParser#ttcdist.
    def enterTtcdist(self, ctx:malParser.TtcdistContext):
        pass

    # Exit a parse tree produced by malParser#ttcdist.
    def exitTtcdist(self, ctx:malParser.TtcdistContext):
        pass


    # Enter a parse tree produced by malParser#precondition.
    def enterPrecondition(self, ctx:malParser.PreconditionContext):
        pass

    # Exit a parse tree produced by malParser#precondition.
    def exitPrecondition(self, ctx:malParser.PreconditionContext):
        pass


    # Enter a parse tree produced by malParser#reaches.
    def enterReaches(self, ctx:malParser.ReachesContext):
        pass

    # Exit a parse tree produced by malParser#reaches.
    def exitReaches(self, ctx:malParser.ReachesContext):
        pass


    # Enter a parse tree produced by malParser#number.
    def enterNumber(self, ctx:malParser.NumberContext):
        pass

    # Exit a parse tree produced by malParser#number.
    def exitNumber(self, ctx:malParser.NumberContext):
        pass


    # Enter a parse tree produced by malParser#variable.
    def enterVariable(self, ctx:malParser.VariableContext):
        pass

    # Exit a parse tree produced by malParser#variable.
    def exitVariable(self, ctx:malParser.VariableContext):
        pass


    # Enter a parse tree produced by malParser#expr.
    def enterExpr(self, ctx:malParser.ExprContext):
        pass

    # Exit a parse tree produced by malParser#expr.
    def exitExpr(self, ctx:malParser.ExprContext):
        pass


    # Enter a parse tree produced by malParser#parts.
    def enterParts(self, ctx:malParser.PartsContext):
        pass

    # Exit a parse tree produced by malParser#parts.
    def exitParts(self, ctx:malParser.PartsContext):
        pass


    # Enter a parse tree produced by malParser#part.
    def enterPart(self, ctx:malParser.PartContext):
        pass

    # Exit a parse tree produced by malParser#part.
    def exitPart(self, ctx:malParser.PartContext):
        pass


    # Enter a parse tree produced by malParser#varsubst.
    def enterVarsubst(self, ctx:malParser.VarsubstContext):
        pass

    # Exit a parse tree produced by malParser#varsubst.
    def exitVarsubst(self, ctx:malParser.VarsubstContext):
        pass


    # Enter a parse tree produced by malParser#type.
    def enterType(self, ctx:malParser.TypeContext):
        pass

    # Exit a parse tree produced by malParser#type.
    def exitType(self, ctx:malParser.TypeContext):
        pass


    # Enter a parse tree produced by malParser#setop.
    def enterSetop(self, ctx:malParser.SetopContext):
        pass

    # Exit a parse tree produced by malParser#setop.
    def exitSetop(self, ctx:malParser.SetopContext):
        pass


    # Enter a parse tree produced by malParser#associations.
    def enterAssociations(self, ctx:malParser.AssociationsContext):
        pass

    # Exit a parse tree produced by malParser#associations.
    def exitAssociations(self, ctx:malParser.AssociationsContext):
        pass


    # Enter a parse tree produced by malParser#association.
    def enterAssociation(self, ctx:malParser.AssociationContext):
        pass

    # Exit a parse tree produced by malParser#association.
    def exitAssociation(self, ctx:malParser.AssociationContext):
        pass


    # Enter a parse tree produced by malParser#field.
    def enterField(self, ctx:malParser.FieldContext):
        pass

    # Exit a parse tree produced by malParser#field.
    def exitField(self, ctx:malParser.FieldContext):
        pass


    # Enter a parse tree produced by malParser#mult.
    def enterMult(self, ctx:malParser.MultContext):
        pass

    # Exit a parse tree produced by malParser#mult.
    def exitMult(self, ctx:malParser.MultContext):
        pass


    # Enter a parse tree produced by malParser#multatom.
    def enterMultatom(self, ctx:malParser.MultatomContext):
        pass

    # Exit a parse tree produced by malParser#multatom.
    def exitMultatom(self, ctx:malParser.MultatomContext):
        pass


    # Enter a parse tree produced by malParser#linkname.
    def enterLinkname(self, ctx:malParser.LinknameContext):
        pass

    # Exit a parse tree produced by malParser#linkname.
    def exitLinkname(self, ctx:malParser.LinknameContext):
        pass



del malParser