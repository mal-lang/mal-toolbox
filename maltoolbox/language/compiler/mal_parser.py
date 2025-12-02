# Generated from maltoolbox/language/compiler/mal.g4 by ANTLR 4.13.2
# encoding: utf-8
from antlr4 import *
from io import StringIO
import sys

if sys.version_info[1] > 5:
    from typing import TextIO
else:
    from typing.io import TextIO


# fmt: off
def serializedATN():
    return [
        4,1,53,420,2,0,7,0,2,1,7,1,2,2,7,2,2,3,7,3,2,4,7,4,2,5,7,5,2,6,7,
        6,2,7,7,7,2,8,7,8,2,9,7,9,2,10,7,10,2,11,7,11,2,12,7,12,2,13,7,13,
        2,14,7,14,2,15,7,15,2,16,7,16,2,17,7,17,2,18,7,18,2,19,7,19,2,20,
        7,20,2,21,7,21,2,22,7,22,2,23,7,23,2,24,7,24,2,25,7,25,2,26,7,26,
        2,27,7,27,2,28,7,28,2,29,7,29,2,30,7,30,2,31,7,31,2,32,7,32,2,33,
        7,33,2,34,7,34,2,35,7,35,2,36,7,36,2,37,7,37,2,38,7,38,2,39,7,39,
        2,40,7,40,2,41,7,41,2,42,7,42,2,43,7,43,2,44,7,44,2,45,7,45,1,0,
        4,0,94,8,0,11,0,12,0,95,1,0,3,0,99,8,0,1,1,1,1,1,1,1,1,3,1,105,8,
        1,1,2,1,2,1,2,1,3,1,3,1,3,1,3,1,3,1,4,1,4,1,4,5,4,118,8,4,10,4,12,
        4,121,9,4,1,4,1,4,5,4,125,8,4,10,4,12,4,128,9,4,1,4,1,4,1,5,1,5,
        1,5,1,5,1,5,1,6,1,6,1,7,3,7,140,8,7,1,7,1,7,1,7,1,7,3,7,146,8,7,
        1,7,5,7,149,8,7,10,7,12,7,152,9,7,1,7,1,7,1,7,5,7,157,8,7,10,7,12,
        7,160,9,7,1,7,1,7,1,8,1,8,3,8,166,8,8,1,8,1,8,5,8,170,8,8,10,8,12,
        8,173,9,8,1,8,3,8,176,8,8,1,8,3,8,179,8,8,1,8,5,8,182,8,8,10,8,12,
        8,185,9,8,1,8,5,8,188,8,8,10,8,12,8,191,9,8,1,8,3,8,194,8,8,1,8,
        3,8,197,8,8,1,9,1,9,1,10,1,10,1,11,1,11,1,11,1,12,1,12,1,12,1,12,
        5,12,210,8,12,10,12,12,12,213,9,12,1,12,1,12,1,13,1,13,1,14,1,14,
        1,15,1,15,1,15,1,15,1,16,1,16,1,16,5,16,228,8,16,10,16,12,16,231,
        9,16,1,17,1,17,1,17,5,17,236,8,17,10,17,12,17,239,9,17,1,18,1,18,
        1,18,3,18,244,8,18,1,19,1,19,1,19,1,19,1,19,1,19,3,19,252,8,19,1,
        20,1,20,1,20,1,20,1,20,5,20,259,8,20,10,20,12,20,262,9,20,3,20,264,
        8,20,1,20,3,20,267,8,20,1,21,1,21,3,21,271,8,21,1,21,1,21,3,21,275,
        8,21,1,21,3,21,278,8,21,1,22,1,22,1,23,1,23,1,23,5,23,285,8,23,10,
        23,12,23,288,9,23,1,24,1,24,1,24,1,24,5,24,294,8,24,10,24,12,24,
        297,9,24,1,24,1,24,1,25,1,25,1,25,1,26,1,26,1,27,1,27,1,28,1,28,
        1,29,1,29,1,30,1,30,1,30,1,30,5,30,316,8,30,10,30,12,30,319,9,30,
        1,31,1,31,1,31,1,31,5,31,325,8,31,10,31,12,31,328,9,31,1,32,1,32,
        1,33,1,33,1,33,1,33,1,33,1,34,1,34,1,34,1,34,5,34,341,8,34,10,34,
        12,34,344,9,34,1,35,1,35,1,35,5,35,349,8,35,10,35,12,35,352,9,35,
        1,36,1,36,1,36,1,36,1,36,1,36,1,36,1,36,1,36,3,36,363,8,36,1,36,
        3,36,366,8,36,1,36,5,36,369,8,36,10,36,12,36,372,9,36,1,37,1,37,
        1,38,1,38,1,38,1,38,1,39,1,39,1,40,1,40,1,40,5,40,385,8,40,10,40,
        12,40,388,9,40,1,40,1,40,1,41,1,41,1,41,1,41,1,41,1,41,1,41,1,41,
        1,41,1,41,5,41,402,8,41,10,41,12,41,405,9,41,1,42,1,42,1,42,1,42,
        1,43,1,43,1,43,3,43,414,8,43,1,44,1,44,1,45,1,45,1,45,0,0,46,0,2,
        4,6,8,10,12,14,16,18,20,22,24,26,28,30,32,34,36,38,40,42,44,46,48,
        50,52,54,56,58,60,62,64,66,68,70,72,74,76,78,80,82,84,86,88,90,0,
        11,1,0,11,12,4,0,15,15,24,24,38,39,41,41,1,0,1,2,1,0,16,18,2,0,33,
        33,47,47,2,0,30,30,48,48,2,0,40,40,50,50,1,0,44,45,1,0,13,14,1,0,
        33,35,2,0,13,13,30,30,418,0,98,1,0,0,0,2,104,1,0,0,0,4,106,1,0,0,
        0,6,109,1,0,0,0,8,114,1,0,0,0,10,131,1,0,0,0,12,136,1,0,0,0,14,139,
        1,0,0,0,16,163,1,0,0,0,18,198,1,0,0,0,20,200,1,0,0,0,22,202,1,0,
        0,0,24,205,1,0,0,0,26,216,1,0,0,0,28,218,1,0,0,0,30,220,1,0,0,0,
        32,224,1,0,0,0,34,232,1,0,0,0,36,240,1,0,0,0,38,251,1,0,0,0,40,253,
        1,0,0,0,42,268,1,0,0,0,44,279,1,0,0,0,46,281,1,0,0,0,48,289,1,0,
        0,0,50,300,1,0,0,0,52,303,1,0,0,0,54,305,1,0,0,0,56,307,1,0,0,0,
        58,309,1,0,0,0,60,311,1,0,0,0,62,320,1,0,0,0,64,329,1,0,0,0,66,331,
        1,0,0,0,68,336,1,0,0,0,70,345,1,0,0,0,72,362,1,0,0,0,74,373,1,0,
        0,0,76,375,1,0,0,0,78,379,1,0,0,0,80,381,1,0,0,0,82,391,1,0,0,0,
        84,406,1,0,0,0,86,410,1,0,0,0,88,415,1,0,0,0,90,417,1,0,0,0,92,94,
        3,2,1,0,93,92,1,0,0,0,94,95,1,0,0,0,95,93,1,0,0,0,95,96,1,0,0,0,
        96,99,1,0,0,0,97,99,5,0,0,1,98,93,1,0,0,0,98,97,1,0,0,0,99,1,1,0,
        0,0,100,105,3,4,2,0,101,105,3,6,3,0,102,105,3,8,4,0,103,105,3,80,
        40,0,104,100,1,0,0,0,104,101,1,0,0,0,104,102,1,0,0,0,104,103,1,0,
        0,0,105,3,1,0,0,0,106,107,5,7,0,0,107,108,5,11,0,0,108,5,1,0,0,0,
        109,110,5,24,0,0,110,111,5,19,0,0,111,112,5,25,0,0,112,113,5,11,
        0,0,113,7,1,0,0,0,114,115,5,8,0,0,115,119,5,19,0,0,116,118,3,10,
        5,0,117,116,1,0,0,0,118,121,1,0,0,0,119,117,1,0,0,0,119,120,1,0,
        0,0,120,122,1,0,0,0,121,119,1,0,0,0,122,126,5,22,0,0,123,125,3,14,
        7,0,124,123,1,0,0,0,125,128,1,0,0,0,126,124,1,0,0,0,126,127,1,0,
        0,0,127,129,1,0,0,0,128,126,1,0,0,0,129,130,5,23,0,0,130,9,1,0,0,
        0,131,132,5,19,0,0,132,133,5,9,0,0,133,134,5,25,0,0,134,135,3,12,
        6,0,135,11,1,0,0,0,136,137,7,0,0,0,137,13,1,0,0,0,138,140,5,3,0,
        0,139,138,1,0,0,0,139,140,1,0,0,0,140,141,1,0,0,0,141,142,5,4,0,
        0,142,145,5,19,0,0,143,144,5,6,0,0,144,146,5,19,0,0,145,143,1,0,
        0,0,145,146,1,0,0,0,146,150,1,0,0,0,147,149,3,10,5,0,148,147,1,0,
        0,0,149,152,1,0,0,0,150,148,1,0,0,0,150,151,1,0,0,0,151,153,1,0,
        0,0,152,150,1,0,0,0,153,158,5,22,0,0,154,157,3,16,8,0,155,157,3,
        66,33,0,156,154,1,0,0,0,156,155,1,0,0,0,157,160,1,0,0,0,158,156,
        1,0,0,0,158,159,1,0,0,0,159,161,1,0,0,0,160,158,1,0,0,0,161,162,
        5,23,0,0,162,15,1,0,0,0,163,165,3,18,9,0,164,166,3,20,10,0,165,164,
        1,0,0,0,165,166,1,0,0,0,166,167,1,0,0,0,167,171,5,19,0,0,168,170,
        3,22,11,0,169,168,1,0,0,0,170,173,1,0,0,0,171,169,1,0,0,0,171,172,
        1,0,0,0,172,175,1,0,0,0,173,171,1,0,0,0,174,176,3,24,12,0,175,174,
        1,0,0,0,175,176,1,0,0,0,176,178,1,0,0,0,177,179,3,30,15,0,178,177,
        1,0,0,0,178,179,1,0,0,0,179,183,1,0,0,0,180,182,3,10,5,0,181,180,
        1,0,0,0,182,185,1,0,0,0,183,181,1,0,0,0,183,184,1,0,0,0,184,189,
        1,0,0,0,185,183,1,0,0,0,186,188,3,42,21,0,187,186,1,0,0,0,188,191,
        1,0,0,0,189,187,1,0,0,0,189,190,1,0,0,0,190,193,1,0,0,0,191,189,
        1,0,0,0,192,194,3,60,30,0,193,192,1,0,0,0,193,194,1,0,0,0,194,196,
        1,0,0,0,195,197,3,62,31,0,196,195,1,0,0,0,196,197,1,0,0,0,197,17,
        1,0,0,0,198,199,7,1,0,0,199,19,1,0,0,0,200,201,7,2,0,0,201,21,1,
        0,0,0,202,203,5,42,0,0,203,204,5,19,0,0,204,23,1,0,0,0,205,206,5,
        22,0,0,206,211,3,26,13,0,207,208,5,46,0,0,208,210,3,26,13,0,209,
        207,1,0,0,0,210,213,1,0,0,0,211,209,1,0,0,0,211,212,1,0,0,0,212,
        214,1,0,0,0,213,211,1,0,0,0,214,215,5,23,0,0,215,25,1,0,0,0,216,
        217,7,3,0,0,217,27,1,0,0,0,218,219,3,30,15,0,219,29,1,0,0,0,220,
        221,5,28,0,0,221,222,3,32,16,0,222,223,5,29,0,0,223,31,1,0,0,0,224,
        229,3,34,17,0,225,226,7,4,0,0,226,228,3,34,17,0,227,225,1,0,0,0,
        228,231,1,0,0,0,229,227,1,0,0,0,229,230,1,0,0,0,230,33,1,0,0,0,231,
        229,1,0,0,0,232,237,3,36,18,0,233,234,7,5,0,0,234,236,3,36,18,0,
        235,233,1,0,0,0,236,239,1,0,0,0,237,235,1,0,0,0,237,238,1,0,0,0,
        238,35,1,0,0,0,239,237,1,0,0,0,240,243,3,38,19,0,241,242,5,49,0,
        0,242,244,3,38,19,0,243,241,1,0,0,0,243,244,1,0,0,0,244,37,1,0,0,
        0,245,252,3,40,20,0,246,247,5,20,0,0,247,248,3,32,16,0,248,249,5,
        21,0,0,249,252,1,0,0,0,250,252,3,64,32,0,251,245,1,0,0,0,251,246,
        1,0,0,0,251,250,1,0,0,0,252,39,1,0,0,0,253,266,5,19,0,0,254,263,
        5,20,0,0,255,260,3,64,32,0,256,257,5,46,0,0,257,259,3,64,32,0,258,
        256,1,0,0,0,259,262,1,0,0,0,260,258,1,0,0,0,260,261,1,0,0,0,261,
        264,1,0,0,0,262,260,1,0,0,0,263,255,1,0,0,0,263,264,1,0,0,0,264,
        265,1,0,0,0,265,267,5,21,0,0,266,254,1,0,0,0,266,267,1,0,0,0,267,
        41,1,0,0,0,268,270,3,44,22,0,269,271,3,46,23,0,270,269,1,0,0,0,270,
        271,1,0,0,0,271,272,1,0,0,0,272,274,3,48,24,0,273,275,3,56,28,0,
        274,273,1,0,0,0,274,275,1,0,0,0,275,277,1,0,0,0,276,278,3,58,29,
        0,277,276,1,0,0,0,277,278,1,0,0,0,278,43,1,0,0,0,279,280,7,6,0,0,
        280,45,1,0,0,0,281,286,5,19,0,0,282,283,5,37,0,0,283,285,5,19,0,
        0,284,282,1,0,0,0,285,288,1,0,0,0,286,284,1,0,0,0,286,287,1,0,0,
        0,287,47,1,0,0,0,288,286,1,0,0,0,289,290,5,20,0,0,290,295,3,50,25,
        0,291,292,5,46,0,0,292,294,3,50,25,0,293,291,1,0,0,0,294,297,1,0,
        0,0,295,293,1,0,0,0,295,296,1,0,0,0,296,298,1,0,0,0,297,295,1,0,
        0,0,298,299,5,21,0,0,299,49,1,0,0,0,300,301,3,52,26,0,301,302,3,
        54,27,0,302,51,1,0,0,0,303,304,5,19,0,0,304,53,1,0,0,0,305,306,5,
        19,0,0,306,55,1,0,0,0,307,308,5,19,0,0,308,57,1,0,0,0,309,310,3,
        30,15,0,310,59,1,0,0,0,311,312,5,43,0,0,312,317,3,68,34,0,313,314,
        5,46,0,0,314,316,3,68,34,0,315,313,1,0,0,0,316,319,1,0,0,0,317,315,
        1,0,0,0,317,318,1,0,0,0,318,61,1,0,0,0,319,317,1,0,0,0,320,321,7,
        7,0,0,321,326,3,68,34,0,322,323,5,46,0,0,323,325,3,68,34,0,324,322,
        1,0,0,0,325,328,1,0,0,0,326,324,1,0,0,0,326,327,1,0,0,0,327,63,1,
        0,0,0,328,326,1,0,0,0,329,330,7,8,0,0,330,65,1,0,0,0,331,332,5,10,
        0,0,332,333,5,19,0,0,333,334,5,32,0,0,334,335,3,68,34,0,335,67,1,
        0,0,0,336,342,3,70,35,0,337,338,3,78,39,0,338,339,3,70,35,0,339,
        341,1,0,0,0,340,337,1,0,0,0,341,344,1,0,0,0,342,340,1,0,0,0,342,
        343,1,0,0,0,343,69,1,0,0,0,344,342,1,0,0,0,345,350,3,72,36,0,346,
        347,5,37,0,0,347,349,3,72,36,0,348,346,1,0,0,0,349,352,1,0,0,0,350,
        348,1,0,0,0,350,351,1,0,0,0,351,71,1,0,0,0,352,350,1,0,0,0,353,354,
        5,20,0,0,354,355,3,68,34,0,355,356,5,21,0,0,356,363,1,0,0,0,357,
        358,3,74,37,0,358,359,5,20,0,0,359,360,5,21,0,0,360,363,1,0,0,0,
        361,363,5,19,0,0,362,353,1,0,0,0,362,357,1,0,0,0,362,361,1,0,0,0,
        363,365,1,0,0,0,364,366,5,30,0,0,365,364,1,0,0,0,365,366,1,0,0,0,
        366,370,1,0,0,0,367,369,3,76,38,0,368,367,1,0,0,0,369,372,1,0,0,
        0,370,368,1,0,0,0,370,371,1,0,0,0,371,73,1,0,0,0,372,370,1,0,0,0,
        373,374,5,19,0,0,374,75,1,0,0,0,375,376,5,28,0,0,376,377,5,19,0,
        0,377,378,5,29,0,0,378,77,1,0,0,0,379,380,7,9,0,0,380,79,1,0,0,0,
        381,382,5,5,0,0,382,386,5,22,0,0,383,385,3,82,41,0,384,383,1,0,0,
        0,385,388,1,0,0,0,386,384,1,0,0,0,386,387,1,0,0,0,387,389,1,0,0,
        0,388,386,1,0,0,0,389,390,5,23,0,0,390,81,1,0,0,0,391,392,5,19,0,
        0,392,393,3,84,42,0,393,394,3,86,43,0,394,395,5,26,0,0,395,396,3,
        90,45,0,396,397,5,27,0,0,397,398,3,86,43,0,398,399,3,84,42,0,399,
        403,5,19,0,0,400,402,3,10,5,0,401,400,1,0,0,0,402,405,1,0,0,0,403,
        401,1,0,0,0,403,404,1,0,0,0,404,83,1,0,0,0,405,403,1,0,0,0,406,407,
        5,28,0,0,407,408,5,19,0,0,408,409,5,29,0,0,409,85,1,0,0,0,410,413,
        3,88,44,0,411,412,5,36,0,0,412,414,3,88,44,0,413,411,1,0,0,0,413,
        414,1,0,0,0,414,87,1,0,0,0,415,416,7,10,0,0,416,89,1,0,0,0,417,418,
        5,19,0,0,418,91,1,0,0,0,41,95,98,104,119,126,139,145,150,156,158,
        165,171,175,178,183,189,193,196,211,229,237,243,251,260,263,266,
        270,274,277,286,295,317,326,342,350,362,365,370,386,403,413
    ]
# fmt: on


class malParser(Parser):
    grammarFileName = 'mal.g4'

    atn = ATNDeserializer().deserialize(serializedATN())

    decisionsToDFA = [DFA(ds, i) for i, ds in enumerate(atn.decisionToState)]

    sharedContextCache = PredictionContextCache()

    literalNames = [
        '<INVALID>',
        "'action'",
        "'effect'",
        "'abstract'",
        "'asset'",
        "'associations'",
        "'extends'",
        "'include'",
        "'category'",
        "'info'",
        "'let'",
        '<INVALID>',
        '<INVALID>',
        '<INVALID>',
        '<INVALID>',
        "'E'",
        "'C'",
        "'I'",
        "'A'",
        '<INVALID>',
        "'('",
        "')'",
        "'{'",
        "'}'",
        "'#'",
        "':'",
        "'<--'",
        "'-->'",
        "'['",
        "']'",
        "'*'",
        "'1'",
        "'='",
        "'-'",
        "'/\\'",
        "'\\/'",
        "'..'",
        "'.'",
        "'&'",
        "'|'",
        "'!'",
        "'!E'",
        "'@'",
        "'<-'",
        "'+>'",
        "'->'",
        "','",
        "'+'",
        "'/'",
        "'^'",
        "'//!'",
    ]

    symbolicNames = [
        '<INVALID>',
        'ACTION',
        'EFFECT',
        'ABSTRACT',
        'ASSET',
        'ASSOCIATIONS',
        'EXTENDS',
        'INCLUDE',
        'CATEGORY',
        'INFO',
        'LET',
        'STRING',
        'MULTILINE_STRING',
        'INT',
        'FLOAT',
        'EXISTS',
        'C',
        'I',
        'A',
        'ID',
        'LPAREN',
        'RPAREN',
        'LCURLY',
        'RCURLY',
        'HASH',
        'COLON',
        'LARROW',
        'RARROW',
        'LSQUARE',
        'RSQUARE',
        'STAR',
        'ONE',
        'ASSIGN',
        'MINUS',
        'INTERSECT',
        'UNION',
        'RANGE',
        'DOT',
        'AND',
        'OR',
        'EXCLAMATION',
        'NOTEXISTS',
        'AT',
        'REQUIRES',
        'INHERITS',
        'LEADSTO',
        'COMMA',
        'PLUS',
        'DIVIDE',
        'POWER',
        'EXCLM_COMM',
        'INLINE_COMMENT',
        'MULTILINE_COMMENT',
        'WS',
    ]

    RULE_mal = 0
    RULE_declaration = 1
    RULE_include = 2
    RULE_define = 3
    RULE_category = 4
    RULE_meta = 5
    RULE_text = 6
    RULE_asset = 7
    RULE_step = 8
    RULE_steptype = 9
    RULE_stepkind = 10
    RULE_tag = 11
    RULE_cias = 12
    RULE_cia = 13
    RULE_ttc = 14
    RULE_pdist = 15
    RULE_pdistexpr = 16
    RULE_pdistterm = 17
    RULE_pdistfact = 18
    RULE_pdistatom = 19
    RULE_pdistdist = 20
    RULE_detector = 21
    RULE_bang = 22
    RULE_detectorname = 23
    RULE_context = 24
    RULE_contextpart = 25
    RULE_contextasset = 26
    RULE_contextlabel = 27
    RULE_detectortype = 28
    RULE_tprate = 29
    RULE_precondition = 30
    RULE_reaches = 31
    RULE_number = 32
    RULE_variable = 33
    RULE_expr = 34
    RULE_parts = 35
    RULE_part = 36
    RULE_varsubst = 37
    RULE_type = 38
    RULE_setop = 39
    RULE_associations = 40
    RULE_association = 41
    RULE_field = 42
    RULE_mult = 43
    RULE_multatom = 44
    RULE_linkname = 45

    ruleNames = [
        'mal',
        'declaration',
        'include',
        'define',
        'category',
        'meta',
        'text',
        'asset',
        'step',
        'steptype',
        'stepkind',
        'tag',
        'cias',
        'cia',
        'ttc',
        'pdist',
        'pdistexpr',
        'pdistterm',
        'pdistfact',
        'pdistatom',
        'pdistdist',
        'detector',
        'bang',
        'detectorname',
        'context',
        'contextpart',
        'contextasset',
        'contextlabel',
        'detectortype',
        'tprate',
        'precondition',
        'reaches',
        'number',
        'variable',
        'expr',
        'parts',
        'part',
        'varsubst',
        'type',
        'setop',
        'associations',
        'association',
        'field',
        'mult',
        'multatom',
        'linkname',
    ]

    EOF = Token.EOF
    ACTION = 1
    EFFECT = 2
    ABSTRACT = 3
    ASSET = 4
    ASSOCIATIONS = 5
    EXTENDS = 6
    INCLUDE = 7
    CATEGORY = 8
    INFO = 9
    LET = 10
    STRING = 11
    MULTILINE_STRING = 12
    INT = 13
    FLOAT = 14
    EXISTS = 15
    C = 16
    I = 17
    A = 18
    ID = 19
    LPAREN = 20
    RPAREN = 21
    LCURLY = 22
    RCURLY = 23
    HASH = 24
    COLON = 25
    LARROW = 26
    RARROW = 27
    LSQUARE = 28
    RSQUARE = 29
    STAR = 30
    ONE = 31
    ASSIGN = 32
    MINUS = 33
    INTERSECT = 34
    UNION = 35
    RANGE = 36
    DOT = 37
    AND = 38
    OR = 39
    EXCLAMATION = 40
    NOTEXISTS = 41
    AT = 42
    REQUIRES = 43
    INHERITS = 44
    LEADSTO = 45
    COMMA = 46
    PLUS = 47
    DIVIDE = 48
    POWER = 49
    EXCLM_COMM = 50
    INLINE_COMMENT = 51
    MULTILINE_COMMENT = 52
    WS = 53

    def __init__(self, input: TokenStream, output: TextIO = sys.stdout):
        super().__init__(input, output)
        self.checkVersion('4.13.2')
        self._interp = ParserATNSimulator(
            self, self.atn, self.decisionsToDFA, self.sharedContextCache
        )
        self._predicates = None

    class MalContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(
            self, parser, parent: ParserRuleContext = None, invokingState: int = -1
        ):
            super().__init__(parent, invokingState)
            self.parser = parser

        def declaration(self, i: int = None):
            if i is None:
                return self.getTypedRuleContexts(malParser.DeclarationContext)
            else:
                return self.getTypedRuleContext(malParser.DeclarationContext, i)

        def EOF(self):
            return self.getToken(malParser.EOF, 0)

        def getRuleIndex(self):
            return malParser.RULE_mal

        def accept(self, visitor: ParseTreeVisitor):
            if hasattr(visitor, 'visitMal'):
                return visitor.visitMal(self)
            else:
                return visitor.visitChildren(self)

    def mal(self):
        localctx = malParser.MalContext(self, self._ctx, self.state)
        self.enterRule(localctx, 0, self.RULE_mal)
        self._la = 0  # Token type
        try:
            self.state = 98
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [5, 7, 8, 24]:
                self.enterOuterAlt(localctx, 1)
                self.state = 93
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                while True:
                    self.state = 92
                    self.declaration()
                    self.state = 95
                    self._errHandler.sync(self)
                    _la = self._input.LA(1)
                    if not (((_la) & ~0x3F) == 0 and ((1 << _la) & 16777632) != 0):
                        break

                pass
            elif token in [-1]:
                self.enterOuterAlt(localctx, 2)
                self.state = 97
                self.match(malParser.EOF)
                pass
            else:
                raise NoViableAltException(self)

        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx

    class DeclarationContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(
            self, parser, parent: ParserRuleContext = None, invokingState: int = -1
        ):
            super().__init__(parent, invokingState)
            self.parser = parser

        def include(self):
            return self.getTypedRuleContext(malParser.IncludeContext, 0)

        def define(self):
            return self.getTypedRuleContext(malParser.DefineContext, 0)

        def category(self):
            return self.getTypedRuleContext(malParser.CategoryContext, 0)

        def associations(self):
            return self.getTypedRuleContext(malParser.AssociationsContext, 0)

        def getRuleIndex(self):
            return malParser.RULE_declaration

        def accept(self, visitor: ParseTreeVisitor):
            if hasattr(visitor, 'visitDeclaration'):
                return visitor.visitDeclaration(self)
            else:
                return visitor.visitChildren(self)

    def declaration(self):
        localctx = malParser.DeclarationContext(self, self._ctx, self.state)
        self.enterRule(localctx, 2, self.RULE_declaration)
        try:
            self.state = 104
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [7]:
                self.enterOuterAlt(localctx, 1)
                self.state = 100
                self.include()
                pass
            elif token in [24]:
                self.enterOuterAlt(localctx, 2)
                self.state = 101
                self.define()
                pass
            elif token in [8]:
                self.enterOuterAlt(localctx, 3)
                self.state = 102
                self.category()
                pass
            elif token in [5]:
                self.enterOuterAlt(localctx, 4)
                self.state = 103
                self.associations()
                pass
            else:
                raise NoViableAltException(self)

        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx

    class IncludeContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(
            self, parser, parent: ParserRuleContext = None, invokingState: int = -1
        ):
            super().__init__(parent, invokingState)
            self.parser = parser

        def INCLUDE(self):
            return self.getToken(malParser.INCLUDE, 0)

        def STRING(self):
            return self.getToken(malParser.STRING, 0)

        def getRuleIndex(self):
            return malParser.RULE_include

        def accept(self, visitor: ParseTreeVisitor):
            if hasattr(visitor, 'visitInclude'):
                return visitor.visitInclude(self)
            else:
                return visitor.visitChildren(self)

    def include(self):
        localctx = malParser.IncludeContext(self, self._ctx, self.state)
        self.enterRule(localctx, 4, self.RULE_include)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 106
            self.match(malParser.INCLUDE)
            self.state = 107
            self.match(malParser.STRING)
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx

    class DefineContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(
            self, parser, parent: ParserRuleContext = None, invokingState: int = -1
        ):
            super().__init__(parent, invokingState)
            self.parser = parser

        def HASH(self):
            return self.getToken(malParser.HASH, 0)

        def ID(self):
            return self.getToken(malParser.ID, 0)

        def COLON(self):
            return self.getToken(malParser.COLON, 0)

        def STRING(self):
            return self.getToken(malParser.STRING, 0)

        def getRuleIndex(self):
            return malParser.RULE_define

        def accept(self, visitor: ParseTreeVisitor):
            if hasattr(visitor, 'visitDefine'):
                return visitor.visitDefine(self)
            else:
                return visitor.visitChildren(self)

    def define(self):
        localctx = malParser.DefineContext(self, self._ctx, self.state)
        self.enterRule(localctx, 6, self.RULE_define)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 109
            self.match(malParser.HASH)
            self.state = 110
            self.match(malParser.ID)
            self.state = 111
            self.match(malParser.COLON)
            self.state = 112
            self.match(malParser.STRING)
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx

    class CategoryContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(
            self, parser, parent: ParserRuleContext = None, invokingState: int = -1
        ):
            super().__init__(parent, invokingState)
            self.parser = parser

        def CATEGORY(self):
            return self.getToken(malParser.CATEGORY, 0)

        def ID(self):
            return self.getToken(malParser.ID, 0)

        def LCURLY(self):
            return self.getToken(malParser.LCURLY, 0)

        def RCURLY(self):
            return self.getToken(malParser.RCURLY, 0)

        def meta(self, i: int = None):
            if i is None:
                return self.getTypedRuleContexts(malParser.MetaContext)
            else:
                return self.getTypedRuleContext(malParser.MetaContext, i)

        def asset(self, i: int = None):
            if i is None:
                return self.getTypedRuleContexts(malParser.AssetContext)
            else:
                return self.getTypedRuleContext(malParser.AssetContext, i)

        def getRuleIndex(self):
            return malParser.RULE_category

        def accept(self, visitor: ParseTreeVisitor):
            if hasattr(visitor, 'visitCategory'):
                return visitor.visitCategory(self)
            else:
                return visitor.visitChildren(self)

    def category(self):
        localctx = malParser.CategoryContext(self, self._ctx, self.state)
        self.enterRule(localctx, 8, self.RULE_category)
        self._la = 0  # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 114
            self.match(malParser.CATEGORY)
            self.state = 115
            self.match(malParser.ID)
            self.state = 119
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la == 19:
                self.state = 116
                self.meta()
                self.state = 121
                self._errHandler.sync(self)
                _la = self._input.LA(1)

            self.state = 122
            self.match(malParser.LCURLY)
            self.state = 126
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la == 3 or _la == 4:
                self.state = 123
                self.asset()
                self.state = 128
                self._errHandler.sync(self)
                _la = self._input.LA(1)

            self.state = 129
            self.match(malParser.RCURLY)
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx

    class MetaContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(
            self, parser, parent: ParserRuleContext = None, invokingState: int = -1
        ):
            super().__init__(parent, invokingState)
            self.parser = parser

        def ID(self):
            return self.getToken(malParser.ID, 0)

        def INFO(self):
            return self.getToken(malParser.INFO, 0)

        def COLON(self):
            return self.getToken(malParser.COLON, 0)

        def text(self):
            return self.getTypedRuleContext(malParser.TextContext, 0)

        def getRuleIndex(self):
            return malParser.RULE_meta

        def accept(self, visitor: ParseTreeVisitor):
            if hasattr(visitor, 'visitMeta'):
                return visitor.visitMeta(self)
            else:
                return visitor.visitChildren(self)

    def meta(self):
        localctx = malParser.MetaContext(self, self._ctx, self.state)
        self.enterRule(localctx, 10, self.RULE_meta)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 131
            self.match(malParser.ID)
            self.state = 132
            self.match(malParser.INFO)
            self.state = 133
            self.match(malParser.COLON)
            self.state = 134
            self.text()
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx

    class TextContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(
            self, parser, parent: ParserRuleContext = None, invokingState: int = -1
        ):
            super().__init__(parent, invokingState)
            self.parser = parser

        def STRING(self):
            return self.getToken(malParser.STRING, 0)

        def MULTILINE_STRING(self):
            return self.getToken(malParser.MULTILINE_STRING, 0)

        def getRuleIndex(self):
            return malParser.RULE_text

        def accept(self, visitor: ParseTreeVisitor):
            if hasattr(visitor, 'visitText'):
                return visitor.visitText(self)
            else:
                return visitor.visitChildren(self)

    def text(self):
        localctx = malParser.TextContext(self, self._ctx, self.state)
        self.enterRule(localctx, 12, self.RULE_text)
        self._la = 0  # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 136
            _la = self._input.LA(1)
            if not (_la == 11 or _la == 12):
                self._errHandler.recoverInline(self)
            else:
                self._errHandler.reportMatch(self)
                self.consume()
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx

    class AssetContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(
            self, parser, parent: ParserRuleContext = None, invokingState: int = -1
        ):
            super().__init__(parent, invokingState)
            self.parser = parser

        def ASSET(self):
            return self.getToken(malParser.ASSET, 0)

        def ID(self, i: int = None):
            if i is None:
                return self.getTokens(malParser.ID)
            else:
                return self.getToken(malParser.ID, i)

        def LCURLY(self):
            return self.getToken(malParser.LCURLY, 0)

        def RCURLY(self):
            return self.getToken(malParser.RCURLY, 0)

        def ABSTRACT(self):
            return self.getToken(malParser.ABSTRACT, 0)

        def EXTENDS(self):
            return self.getToken(malParser.EXTENDS, 0)

        def meta(self, i: int = None):
            if i is None:
                return self.getTypedRuleContexts(malParser.MetaContext)
            else:
                return self.getTypedRuleContext(malParser.MetaContext, i)

        def step(self, i: int = None):
            if i is None:
                return self.getTypedRuleContexts(malParser.StepContext)
            else:
                return self.getTypedRuleContext(malParser.StepContext, i)

        def variable(self, i: int = None):
            if i is None:
                return self.getTypedRuleContexts(malParser.VariableContext)
            else:
                return self.getTypedRuleContext(malParser.VariableContext, i)

        def getRuleIndex(self):
            return malParser.RULE_asset

        def accept(self, visitor: ParseTreeVisitor):
            if hasattr(visitor, 'visitAsset'):
                return visitor.visitAsset(self)
            else:
                return visitor.visitChildren(self)

    def asset(self):
        localctx = malParser.AssetContext(self, self._ctx, self.state)
        self.enterRule(localctx, 14, self.RULE_asset)
        self._la = 0  # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 139
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la == 3:
                self.state = 138
                self.match(malParser.ABSTRACT)

            self.state = 141
            self.match(malParser.ASSET)
            self.state = 142
            self.match(malParser.ID)
            self.state = 145
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la == 6:
                self.state = 143
                self.match(malParser.EXTENDS)
                self.state = 144
                self.match(malParser.ID)

            self.state = 150
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la == 19:
                self.state = 147
                self.meta()
                self.state = 152
                self._errHandler.sync(self)
                _la = self._input.LA(1)

            self.state = 153
            self.match(malParser.LCURLY)
            self.state = 158
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while ((_la) & ~0x3F) == 0 and ((1 << _la) & 3023673787392) != 0:
                self.state = 156
                self._errHandler.sync(self)
                token = self._input.LA(1)
                if token in [15, 24, 38, 39, 41]:
                    self.state = 154
                    self.step()
                    pass
                elif token in [10]:
                    self.state = 155
                    self.variable()
                    pass
                else:
                    raise NoViableAltException(self)

                self.state = 160
                self._errHandler.sync(self)
                _la = self._input.LA(1)

            self.state = 161
            self.match(malParser.RCURLY)
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx

    class StepContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(
            self, parser, parent: ParserRuleContext = None, invokingState: int = -1
        ):
            super().__init__(parent, invokingState)
            self.parser = parser

        def steptype(self):
            return self.getTypedRuleContext(malParser.SteptypeContext, 0)

        def ID(self):
            return self.getToken(malParser.ID, 0)

        def stepkind(self):
            return self.getTypedRuleContext(malParser.StepkindContext, 0)

        def tag(self, i: int = None):
            if i is None:
                return self.getTypedRuleContexts(malParser.TagContext)
            else:
                return self.getTypedRuleContext(malParser.TagContext, i)

        def cias(self):
            return self.getTypedRuleContext(malParser.CiasContext, 0)

        def pdist(self):
            return self.getTypedRuleContext(malParser.PdistContext, 0)

        def meta(self, i: int = None):
            if i is None:
                return self.getTypedRuleContexts(malParser.MetaContext)
            else:
                return self.getTypedRuleContext(malParser.MetaContext, i)

        def detector(self, i: int = None):
            if i is None:
                return self.getTypedRuleContexts(malParser.DetectorContext)
            else:
                return self.getTypedRuleContext(malParser.DetectorContext, i)

        def precondition(self):
            return self.getTypedRuleContext(malParser.PreconditionContext, 0)

        def reaches(self):
            return self.getTypedRuleContext(malParser.ReachesContext, 0)

        def getRuleIndex(self):
            return malParser.RULE_step

        def accept(self, visitor: ParseTreeVisitor):
            if hasattr(visitor, 'visitStep'):
                return visitor.visitStep(self)
            else:
                return visitor.visitChildren(self)

    def step(self):
        localctx = malParser.StepContext(self, self._ctx, self.state)
        self.enterRule(localctx, 16, self.RULE_step)
        self._la = 0  # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 163
            self.steptype()
            self.state = 165
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la == 1 or _la == 2:
                self.state = 164
                self.stepkind()

            self.state = 167
            self.match(malParser.ID)
            self.state = 171
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la == 42:
                self.state = 168
                self.tag()
                self.state = 173
                self._errHandler.sync(self)
                _la = self._input.LA(1)

            self.state = 175
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la == 22:
                self.state = 174
                self.cias()

            self.state = 178
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la == 28:
                self.state = 177
                self.pdist()

            self.state = 183
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la == 19:
                self.state = 180
                self.meta()
                self.state = 185
                self._errHandler.sync(self)
                _la = self._input.LA(1)

            self.state = 189
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la == 40 or _la == 50:
                self.state = 186
                self.detector()
                self.state = 191
                self._errHandler.sync(self)
                _la = self._input.LA(1)

            self.state = 193
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la == 43:
                self.state = 192
                self.precondition()

            self.state = 196
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la == 44 or _la == 45:
                self.state = 195
                self.reaches()

        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx

    class SteptypeContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(
            self, parser, parent: ParserRuleContext = None, invokingState: int = -1
        ):
            super().__init__(parent, invokingState)
            self.parser = parser

        def AND(self):
            return self.getToken(malParser.AND, 0)

        def OR(self):
            return self.getToken(malParser.OR, 0)

        def HASH(self):
            return self.getToken(malParser.HASH, 0)

        def EXISTS(self):
            return self.getToken(malParser.EXISTS, 0)

        def NOTEXISTS(self):
            return self.getToken(malParser.NOTEXISTS, 0)

        def getRuleIndex(self):
            return malParser.RULE_steptype

        def accept(self, visitor: ParseTreeVisitor):
            if hasattr(visitor, 'visitSteptype'):
                return visitor.visitSteptype(self)
            else:
                return visitor.visitChildren(self)

    def steptype(self):
        localctx = malParser.SteptypeContext(self, self._ctx, self.state)
        self.enterRule(localctx, 18, self.RULE_steptype)
        self._la = 0  # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 198
            _la = self._input.LA(1)
            if not (((_la) & ~0x3F) == 0 and ((1 << _la) & 3023673786368) != 0):
                self._errHandler.recoverInline(self)
            else:
                self._errHandler.reportMatch(self)
                self.consume()
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx

    class StepkindContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(
            self, parser, parent: ParserRuleContext = None, invokingState: int = -1
        ):
            super().__init__(parent, invokingState)
            self.parser = parser

        def ACTION(self):
            return self.getToken(malParser.ACTION, 0)

        def EFFECT(self):
            return self.getToken(malParser.EFFECT, 0)

        def getRuleIndex(self):
            return malParser.RULE_stepkind

        def accept(self, visitor: ParseTreeVisitor):
            if hasattr(visitor, 'visitStepkind'):
                return visitor.visitStepkind(self)
            else:
                return visitor.visitChildren(self)

    def stepkind(self):
        localctx = malParser.StepkindContext(self, self._ctx, self.state)
        self.enterRule(localctx, 20, self.RULE_stepkind)
        self._la = 0  # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 200
            _la = self._input.LA(1)
            if not (_la == 1 or _la == 2):
                self._errHandler.recoverInline(self)
            else:
                self._errHandler.reportMatch(self)
                self.consume()
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx

    class TagContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(
            self, parser, parent: ParserRuleContext = None, invokingState: int = -1
        ):
            super().__init__(parent, invokingState)
            self.parser = parser

        def AT(self):
            return self.getToken(malParser.AT, 0)

        def ID(self):
            return self.getToken(malParser.ID, 0)

        def getRuleIndex(self):
            return malParser.RULE_tag

        def accept(self, visitor: ParseTreeVisitor):
            if hasattr(visitor, 'visitTag'):
                return visitor.visitTag(self)
            else:
                return visitor.visitChildren(self)

    def tag(self):
        localctx = malParser.TagContext(self, self._ctx, self.state)
        self.enterRule(localctx, 22, self.RULE_tag)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 202
            self.match(malParser.AT)
            self.state = 203
            self.match(malParser.ID)
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx

    class CiasContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(
            self, parser, parent: ParserRuleContext = None, invokingState: int = -1
        ):
            super().__init__(parent, invokingState)
            self.parser = parser

        def LCURLY(self):
            return self.getToken(malParser.LCURLY, 0)

        def cia(self, i: int = None):
            if i is None:
                return self.getTypedRuleContexts(malParser.CiaContext)
            else:
                return self.getTypedRuleContext(malParser.CiaContext, i)

        def RCURLY(self):
            return self.getToken(malParser.RCURLY, 0)

        def COMMA(self, i: int = None):
            if i is None:
                return self.getTokens(malParser.COMMA)
            else:
                return self.getToken(malParser.COMMA, i)

        def getRuleIndex(self):
            return malParser.RULE_cias

        def accept(self, visitor: ParseTreeVisitor):
            if hasattr(visitor, 'visitCias'):
                return visitor.visitCias(self)
            else:
                return visitor.visitChildren(self)

    def cias(self):
        localctx = malParser.CiasContext(self, self._ctx, self.state)
        self.enterRule(localctx, 24, self.RULE_cias)
        self._la = 0  # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 205
            self.match(malParser.LCURLY)
            self.state = 206
            self.cia()
            self.state = 211
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la == 46:
                self.state = 207
                self.match(malParser.COMMA)
                self.state = 208
                self.cia()
                self.state = 213
                self._errHandler.sync(self)
                _la = self._input.LA(1)

            self.state = 214
            self.match(malParser.RCURLY)
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx

    class CiaContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(
            self, parser, parent: ParserRuleContext = None, invokingState: int = -1
        ):
            super().__init__(parent, invokingState)
            self.parser = parser

        def C(self):
            return self.getToken(malParser.C, 0)

        def I(self):
            return self.getToken(malParser.I, 0)

        def A(self):
            return self.getToken(malParser.A, 0)

        def getRuleIndex(self):
            return malParser.RULE_cia

        def accept(self, visitor: ParseTreeVisitor):
            if hasattr(visitor, 'visitCia'):
                return visitor.visitCia(self)
            else:
                return visitor.visitChildren(self)

    def cia(self):
        localctx = malParser.CiaContext(self, self._ctx, self.state)
        self.enterRule(localctx, 26, self.RULE_cia)
        self._la = 0  # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 216
            _la = self._input.LA(1)
            if not (((_la) & ~0x3F) == 0 and ((1 << _la) & 458752) != 0):
                self._errHandler.recoverInline(self)
            else:
                self._errHandler.reportMatch(self)
                self.consume()
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx

    class TtcContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(
            self, parser, parent: ParserRuleContext = None, invokingState: int = -1
        ):
            super().__init__(parent, invokingState)
            self.parser = parser

        def pdist(self):
            return self.getTypedRuleContext(malParser.PdistContext, 0)

        def getRuleIndex(self):
            return malParser.RULE_ttc

        def accept(self, visitor: ParseTreeVisitor):
            if hasattr(visitor, 'visitTtc'):
                return visitor.visitTtc(self)
            else:
                return visitor.visitChildren(self)

    def ttc(self):
        localctx = malParser.TtcContext(self, self._ctx, self.state)
        self.enterRule(localctx, 28, self.RULE_ttc)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 218
            self.pdist()
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx

    class PdistContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(
            self, parser, parent: ParserRuleContext = None, invokingState: int = -1
        ):
            super().__init__(parent, invokingState)
            self.parser = parser

        def LSQUARE(self):
            return self.getToken(malParser.LSQUARE, 0)

        def pdistexpr(self):
            return self.getTypedRuleContext(malParser.PdistexprContext, 0)

        def RSQUARE(self):
            return self.getToken(malParser.RSQUARE, 0)

        def getRuleIndex(self):
            return malParser.RULE_pdist

        def accept(self, visitor: ParseTreeVisitor):
            if hasattr(visitor, 'visitPdist'):
                return visitor.visitPdist(self)
            else:
                return visitor.visitChildren(self)

    def pdist(self):
        localctx = malParser.PdistContext(self, self._ctx, self.state)
        self.enterRule(localctx, 30, self.RULE_pdist)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 220
            self.match(malParser.LSQUARE)
            self.state = 221
            self.pdistexpr()
            self.state = 222
            self.match(malParser.RSQUARE)
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx

    class PdistexprContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(
            self, parser, parent: ParserRuleContext = None, invokingState: int = -1
        ):
            super().__init__(parent, invokingState)
            self.parser = parser

        def pdistterm(self, i: int = None):
            if i is None:
                return self.getTypedRuleContexts(malParser.PdisttermContext)
            else:
                return self.getTypedRuleContext(malParser.PdisttermContext, i)

        def PLUS(self, i: int = None):
            if i is None:
                return self.getTokens(malParser.PLUS)
            else:
                return self.getToken(malParser.PLUS, i)

        def MINUS(self, i: int = None):
            if i is None:
                return self.getTokens(malParser.MINUS)
            else:
                return self.getToken(malParser.MINUS, i)

        def getRuleIndex(self):
            return malParser.RULE_pdistexpr

        def accept(self, visitor: ParseTreeVisitor):
            if hasattr(visitor, 'visitPdistexpr'):
                return visitor.visitPdistexpr(self)
            else:
                return visitor.visitChildren(self)

    def pdistexpr(self):
        localctx = malParser.PdistexprContext(self, self._ctx, self.state)
        self.enterRule(localctx, 32, self.RULE_pdistexpr)
        self._la = 0  # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 224
            self.pdistterm()
            self.state = 229
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la == 33 or _la == 47:
                self.state = 225
                _la = self._input.LA(1)
                if not (_la == 33 or _la == 47):
                    self._errHandler.recoverInline(self)
                else:
                    self._errHandler.reportMatch(self)
                    self.consume()
                self.state = 226
                self.pdistterm()
                self.state = 231
                self._errHandler.sync(self)
                _la = self._input.LA(1)

        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx

    class PdisttermContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(
            self, parser, parent: ParserRuleContext = None, invokingState: int = -1
        ):
            super().__init__(parent, invokingState)
            self.parser = parser

        def pdistfact(self, i: int = None):
            if i is None:
                return self.getTypedRuleContexts(malParser.PdistfactContext)
            else:
                return self.getTypedRuleContext(malParser.PdistfactContext, i)

        def STAR(self, i: int = None):
            if i is None:
                return self.getTokens(malParser.STAR)
            else:
                return self.getToken(malParser.STAR, i)

        def DIVIDE(self, i: int = None):
            if i is None:
                return self.getTokens(malParser.DIVIDE)
            else:
                return self.getToken(malParser.DIVIDE, i)

        def getRuleIndex(self):
            return malParser.RULE_pdistterm

        def accept(self, visitor: ParseTreeVisitor):
            if hasattr(visitor, 'visitPdistterm'):
                return visitor.visitPdistterm(self)
            else:
                return visitor.visitChildren(self)

    def pdistterm(self):
        localctx = malParser.PdisttermContext(self, self._ctx, self.state)
        self.enterRule(localctx, 34, self.RULE_pdistterm)
        self._la = 0  # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 232
            self.pdistfact()
            self.state = 237
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la == 30 or _la == 48:
                self.state = 233
                _la = self._input.LA(1)
                if not (_la == 30 or _la == 48):
                    self._errHandler.recoverInline(self)
                else:
                    self._errHandler.reportMatch(self)
                    self.consume()
                self.state = 234
                self.pdistfact()
                self.state = 239
                self._errHandler.sync(self)
                _la = self._input.LA(1)

        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx

    class PdistfactContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(
            self, parser, parent: ParserRuleContext = None, invokingState: int = -1
        ):
            super().__init__(parent, invokingState)
            self.parser = parser

        def pdistatom(self, i: int = None):
            if i is None:
                return self.getTypedRuleContexts(malParser.PdistatomContext)
            else:
                return self.getTypedRuleContext(malParser.PdistatomContext, i)

        def POWER(self):
            return self.getToken(malParser.POWER, 0)

        def getRuleIndex(self):
            return malParser.RULE_pdistfact

        def accept(self, visitor: ParseTreeVisitor):
            if hasattr(visitor, 'visitPdistfact'):
                return visitor.visitPdistfact(self)
            else:
                return visitor.visitChildren(self)

    def pdistfact(self):
        localctx = malParser.PdistfactContext(self, self._ctx, self.state)
        self.enterRule(localctx, 36, self.RULE_pdistfact)
        self._la = 0  # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 240
            self.pdistatom()
            self.state = 243
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la == 49:
                self.state = 241
                self.match(malParser.POWER)
                self.state = 242
                self.pdistatom()

        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx

    class PdistatomContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(
            self, parser, parent: ParserRuleContext = None, invokingState: int = -1
        ):
            super().__init__(parent, invokingState)
            self.parser = parser

        def pdistdist(self):
            return self.getTypedRuleContext(malParser.PdistdistContext, 0)

        def LPAREN(self):
            return self.getToken(malParser.LPAREN, 0)

        def pdistexpr(self):
            return self.getTypedRuleContext(malParser.PdistexprContext, 0)

        def RPAREN(self):
            return self.getToken(malParser.RPAREN, 0)

        def number(self):
            return self.getTypedRuleContext(malParser.NumberContext, 0)

        def getRuleIndex(self):
            return malParser.RULE_pdistatom

        def accept(self, visitor: ParseTreeVisitor):
            if hasattr(visitor, 'visitPdistatom'):
                return visitor.visitPdistatom(self)
            else:
                return visitor.visitChildren(self)

    def pdistatom(self):
        localctx = malParser.PdistatomContext(self, self._ctx, self.state)
        self.enterRule(localctx, 38, self.RULE_pdistatom)
        try:
            self.state = 251
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [19]:
                self.enterOuterAlt(localctx, 1)
                self.state = 245
                self.pdistdist()
                pass
            elif token in [20]:
                self.enterOuterAlt(localctx, 2)
                self.state = 246
                self.match(malParser.LPAREN)
                self.state = 247
                self.pdistexpr()
                self.state = 248
                self.match(malParser.RPAREN)
                pass
            elif token in [13, 14]:
                self.enterOuterAlt(localctx, 3)
                self.state = 250
                self.number()
                pass
            else:
                raise NoViableAltException(self)

        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx

    class PdistdistContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(
            self, parser, parent: ParserRuleContext = None, invokingState: int = -1
        ):
            super().__init__(parent, invokingState)
            self.parser = parser

        def ID(self):
            return self.getToken(malParser.ID, 0)

        def LPAREN(self):
            return self.getToken(malParser.LPAREN, 0)

        def RPAREN(self):
            return self.getToken(malParser.RPAREN, 0)

        def number(self, i: int = None):
            if i is None:
                return self.getTypedRuleContexts(malParser.NumberContext)
            else:
                return self.getTypedRuleContext(malParser.NumberContext, i)

        def COMMA(self, i: int = None):
            if i is None:
                return self.getTokens(malParser.COMMA)
            else:
                return self.getToken(malParser.COMMA, i)

        def getRuleIndex(self):
            return malParser.RULE_pdistdist

        def accept(self, visitor: ParseTreeVisitor):
            if hasattr(visitor, 'visitPdistdist'):
                return visitor.visitPdistdist(self)
            else:
                return visitor.visitChildren(self)

    def pdistdist(self):
        localctx = malParser.PdistdistContext(self, self._ctx, self.state)
        self.enterRule(localctx, 40, self.RULE_pdistdist)
        self._la = 0  # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 253
            self.match(malParser.ID)
            self.state = 266
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la == 20:
                self.state = 254
                self.match(malParser.LPAREN)
                self.state = 263
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la == 13 or _la == 14:
                    self.state = 255
                    self.number()
                    self.state = 260
                    self._errHandler.sync(self)
                    _la = self._input.LA(1)
                    while _la == 46:
                        self.state = 256
                        self.match(malParser.COMMA)
                        self.state = 257
                        self.number()
                        self.state = 262
                        self._errHandler.sync(self)
                        _la = self._input.LA(1)

                self.state = 265
                self.match(malParser.RPAREN)

        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx

    class DetectorContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(
            self, parser, parent: ParserRuleContext = None, invokingState: int = -1
        ):
            super().__init__(parent, invokingState)
            self.parser = parser

        def bang(self):
            return self.getTypedRuleContext(malParser.BangContext, 0)

        def context(self):
            return self.getTypedRuleContext(malParser.ContextContext, 0)

        def detectorname(self):
            return self.getTypedRuleContext(malParser.DetectornameContext, 0)

        def detectortype(self):
            return self.getTypedRuleContext(malParser.DetectortypeContext, 0)

        def tprate(self):
            return self.getTypedRuleContext(malParser.TprateContext, 0)

        def getRuleIndex(self):
            return malParser.RULE_detector

        def accept(self, visitor: ParseTreeVisitor):
            if hasattr(visitor, 'visitDetector'):
                return visitor.visitDetector(self)
            else:
                return visitor.visitChildren(self)

    def detector(self):
        localctx = malParser.DetectorContext(self, self._ctx, self.state)
        self.enterRule(localctx, 42, self.RULE_detector)
        self._la = 0  # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 268
            self.bang()
            self.state = 270
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la == 19:
                self.state = 269
                self.detectorname()

            self.state = 272
            self.context()
            self.state = 274
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la == 19:
                self.state = 273
                self.detectortype()

            self.state = 277
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la == 28:
                self.state = 276
                self.tprate()

        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx

    class BangContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(
            self, parser, parent: ParserRuleContext = None, invokingState: int = -1
        ):
            super().__init__(parent, invokingState)
            self.parser = parser

        def EXCLAMATION(self):
            return self.getToken(malParser.EXCLAMATION, 0)

        def EXCLM_COMM(self):
            return self.getToken(malParser.EXCLM_COMM, 0)

        def getRuleIndex(self):
            return malParser.RULE_bang

        def accept(self, visitor: ParseTreeVisitor):
            if hasattr(visitor, 'visitBang'):
                return visitor.visitBang(self)
            else:
                return visitor.visitChildren(self)

    def bang(self):
        localctx = malParser.BangContext(self, self._ctx, self.state)
        self.enterRule(localctx, 44, self.RULE_bang)
        self._la = 0  # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 279
            _la = self._input.LA(1)
            if not (_la == 40 or _la == 50):
                self._errHandler.recoverInline(self)
            else:
                self._errHandler.reportMatch(self)
                self.consume()
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx

    class DetectornameContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(
            self, parser, parent: ParserRuleContext = None, invokingState: int = -1
        ):
            super().__init__(parent, invokingState)
            self.parser = parser

        def ID(self, i: int = None):
            if i is None:
                return self.getTokens(malParser.ID)
            else:
                return self.getToken(malParser.ID, i)

        def DOT(self, i: int = None):
            if i is None:
                return self.getTokens(malParser.DOT)
            else:
                return self.getToken(malParser.DOT, i)

        def getRuleIndex(self):
            return malParser.RULE_detectorname

        def accept(self, visitor: ParseTreeVisitor):
            if hasattr(visitor, 'visitDetectorname'):
                return visitor.visitDetectorname(self)
            else:
                return visitor.visitChildren(self)

    def detectorname(self):
        localctx = malParser.DetectornameContext(self, self._ctx, self.state)
        self.enterRule(localctx, 46, self.RULE_detectorname)
        self._la = 0  # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 281
            self.match(malParser.ID)
            self.state = 286
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la == 37:
                self.state = 282
                self.match(malParser.DOT)
                self.state = 283
                self.match(malParser.ID)
                self.state = 288
                self._errHandler.sync(self)
                _la = self._input.LA(1)

        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx

    class ContextContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(
            self, parser, parent: ParserRuleContext = None, invokingState: int = -1
        ):
            super().__init__(parent, invokingState)
            self.parser = parser

        def LPAREN(self):
            return self.getToken(malParser.LPAREN, 0)

        def contextpart(self, i: int = None):
            if i is None:
                return self.getTypedRuleContexts(malParser.ContextpartContext)
            else:
                return self.getTypedRuleContext(malParser.ContextpartContext, i)

        def RPAREN(self):
            return self.getToken(malParser.RPAREN, 0)

        def COMMA(self, i: int = None):
            if i is None:
                return self.getTokens(malParser.COMMA)
            else:
                return self.getToken(malParser.COMMA, i)

        def getRuleIndex(self):
            return malParser.RULE_context

        def accept(self, visitor: ParseTreeVisitor):
            if hasattr(visitor, 'visitContext'):
                return visitor.visitContext(self)
            else:
                return visitor.visitChildren(self)

    def context(self):
        localctx = malParser.ContextContext(self, self._ctx, self.state)
        self.enterRule(localctx, 48, self.RULE_context)
        self._la = 0  # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 289
            self.match(malParser.LPAREN)
            self.state = 290
            self.contextpart()
            self.state = 295
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la == 46:
                self.state = 291
                self.match(malParser.COMMA)
                self.state = 292
                self.contextpart()
                self.state = 297
                self._errHandler.sync(self)
                _la = self._input.LA(1)

            self.state = 298
            self.match(malParser.RPAREN)
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx

    class ContextpartContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(
            self, parser, parent: ParserRuleContext = None, invokingState: int = -1
        ):
            super().__init__(parent, invokingState)
            self.parser = parser

        def contextasset(self):
            return self.getTypedRuleContext(malParser.ContextassetContext, 0)

        def contextlabel(self):
            return self.getTypedRuleContext(malParser.ContextlabelContext, 0)

        def getRuleIndex(self):
            return malParser.RULE_contextpart

        def accept(self, visitor: ParseTreeVisitor):
            if hasattr(visitor, 'visitContextpart'):
                return visitor.visitContextpart(self)
            else:
                return visitor.visitChildren(self)

    def contextpart(self):
        localctx = malParser.ContextpartContext(self, self._ctx, self.state)
        self.enterRule(localctx, 50, self.RULE_contextpart)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 300
            self.contextasset()
            self.state = 301
            self.contextlabel()
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx

    class ContextassetContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(
            self, parser, parent: ParserRuleContext = None, invokingState: int = -1
        ):
            super().__init__(parent, invokingState)
            self.parser = parser

        def ID(self):
            return self.getToken(malParser.ID, 0)

        def getRuleIndex(self):
            return malParser.RULE_contextasset

        def accept(self, visitor: ParseTreeVisitor):
            if hasattr(visitor, 'visitContextasset'):
                return visitor.visitContextasset(self)
            else:
                return visitor.visitChildren(self)

    def contextasset(self):
        localctx = malParser.ContextassetContext(self, self._ctx, self.state)
        self.enterRule(localctx, 52, self.RULE_contextasset)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 303
            self.match(malParser.ID)
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx

    class ContextlabelContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(
            self, parser, parent: ParserRuleContext = None, invokingState: int = -1
        ):
            super().__init__(parent, invokingState)
            self.parser = parser

        def ID(self):
            return self.getToken(malParser.ID, 0)

        def getRuleIndex(self):
            return malParser.RULE_contextlabel

        def accept(self, visitor: ParseTreeVisitor):
            if hasattr(visitor, 'visitContextlabel'):
                return visitor.visitContextlabel(self)
            else:
                return visitor.visitChildren(self)

    def contextlabel(self):
        localctx = malParser.ContextlabelContext(self, self._ctx, self.state)
        self.enterRule(localctx, 54, self.RULE_contextlabel)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 305
            self.match(malParser.ID)
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx

    class DetectortypeContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(
            self, parser, parent: ParserRuleContext = None, invokingState: int = -1
        ):
            super().__init__(parent, invokingState)
            self.parser = parser

        def ID(self):
            return self.getToken(malParser.ID, 0)

        def getRuleIndex(self):
            return malParser.RULE_detectortype

        def accept(self, visitor: ParseTreeVisitor):
            if hasattr(visitor, 'visitDetectortype'):
                return visitor.visitDetectortype(self)
            else:
                return visitor.visitChildren(self)

    def detectortype(self):
        localctx = malParser.DetectortypeContext(self, self._ctx, self.state)
        self.enterRule(localctx, 56, self.RULE_detectortype)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 307
            self.match(malParser.ID)
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx

    class TprateContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(
            self, parser, parent: ParserRuleContext = None, invokingState: int = -1
        ):
            super().__init__(parent, invokingState)
            self.parser = parser

        def pdist(self):
            return self.getTypedRuleContext(malParser.PdistContext, 0)

        def getRuleIndex(self):
            return malParser.RULE_tprate

        def accept(self, visitor: ParseTreeVisitor):
            if hasattr(visitor, 'visitTprate'):
                return visitor.visitTprate(self)
            else:
                return visitor.visitChildren(self)

    def tprate(self):
        localctx = malParser.TprateContext(self, self._ctx, self.state)
        self.enterRule(localctx, 58, self.RULE_tprate)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 309
            self.pdist()
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx

    class PreconditionContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(
            self, parser, parent: ParserRuleContext = None, invokingState: int = -1
        ):
            super().__init__(parent, invokingState)
            self.parser = parser

        def REQUIRES(self):
            return self.getToken(malParser.REQUIRES, 0)

        def expr(self, i: int = None):
            if i is None:
                return self.getTypedRuleContexts(malParser.ExprContext)
            else:
                return self.getTypedRuleContext(malParser.ExprContext, i)

        def COMMA(self, i: int = None):
            if i is None:
                return self.getTokens(malParser.COMMA)
            else:
                return self.getToken(malParser.COMMA, i)

        def getRuleIndex(self):
            return malParser.RULE_precondition

        def accept(self, visitor: ParseTreeVisitor):
            if hasattr(visitor, 'visitPrecondition'):
                return visitor.visitPrecondition(self)
            else:
                return visitor.visitChildren(self)

    def precondition(self):
        localctx = malParser.PreconditionContext(self, self._ctx, self.state)
        self.enterRule(localctx, 60, self.RULE_precondition)
        self._la = 0  # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 311
            self.match(malParser.REQUIRES)
            self.state = 312
            self.expr()
            self.state = 317
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la == 46:
                self.state = 313
                self.match(malParser.COMMA)
                self.state = 314
                self.expr()
                self.state = 319
                self._errHandler.sync(self)
                _la = self._input.LA(1)

        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx

    class ReachesContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(
            self, parser, parent: ParserRuleContext = None, invokingState: int = -1
        ):
            super().__init__(parent, invokingState)
            self.parser = parser

        def expr(self, i: int = None):
            if i is None:
                return self.getTypedRuleContexts(malParser.ExprContext)
            else:
                return self.getTypedRuleContext(malParser.ExprContext, i)

        def INHERITS(self):
            return self.getToken(malParser.INHERITS, 0)

        def LEADSTO(self):
            return self.getToken(malParser.LEADSTO, 0)

        def COMMA(self, i: int = None):
            if i is None:
                return self.getTokens(malParser.COMMA)
            else:
                return self.getToken(malParser.COMMA, i)

        def getRuleIndex(self):
            return malParser.RULE_reaches

        def accept(self, visitor: ParseTreeVisitor):
            if hasattr(visitor, 'visitReaches'):
                return visitor.visitReaches(self)
            else:
                return visitor.visitChildren(self)

    def reaches(self):
        localctx = malParser.ReachesContext(self, self._ctx, self.state)
        self.enterRule(localctx, 62, self.RULE_reaches)
        self._la = 0  # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 320
            _la = self._input.LA(1)
            if not (_la == 44 or _la == 45):
                self._errHandler.recoverInline(self)
            else:
                self._errHandler.reportMatch(self)
                self.consume()
            self.state = 321
            self.expr()
            self.state = 326
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la == 46:
                self.state = 322
                self.match(malParser.COMMA)
                self.state = 323
                self.expr()
                self.state = 328
                self._errHandler.sync(self)
                _la = self._input.LA(1)

        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx

    class NumberContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(
            self, parser, parent: ParserRuleContext = None, invokingState: int = -1
        ):
            super().__init__(parent, invokingState)
            self.parser = parser

        def INT(self):
            return self.getToken(malParser.INT, 0)

        def FLOAT(self):
            return self.getToken(malParser.FLOAT, 0)

        def getRuleIndex(self):
            return malParser.RULE_number

        def accept(self, visitor: ParseTreeVisitor):
            if hasattr(visitor, 'visitNumber'):
                return visitor.visitNumber(self)
            else:
                return visitor.visitChildren(self)

    def number(self):
        localctx = malParser.NumberContext(self, self._ctx, self.state)
        self.enterRule(localctx, 64, self.RULE_number)
        self._la = 0  # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 329
            _la = self._input.LA(1)
            if not (_la == 13 or _la == 14):
                self._errHandler.recoverInline(self)
            else:
                self._errHandler.reportMatch(self)
                self.consume()
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx

    class VariableContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(
            self, parser, parent: ParserRuleContext = None, invokingState: int = -1
        ):
            super().__init__(parent, invokingState)
            self.parser = parser

        def LET(self):
            return self.getToken(malParser.LET, 0)

        def ID(self):
            return self.getToken(malParser.ID, 0)

        def ASSIGN(self):
            return self.getToken(malParser.ASSIGN, 0)

        def expr(self):
            return self.getTypedRuleContext(malParser.ExprContext, 0)

        def getRuleIndex(self):
            return malParser.RULE_variable

        def accept(self, visitor: ParseTreeVisitor):
            if hasattr(visitor, 'visitVariable'):
                return visitor.visitVariable(self)
            else:
                return visitor.visitChildren(self)

    def variable(self):
        localctx = malParser.VariableContext(self, self._ctx, self.state)
        self.enterRule(localctx, 66, self.RULE_variable)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 331
            self.match(malParser.LET)
            self.state = 332
            self.match(malParser.ID)
            self.state = 333
            self.match(malParser.ASSIGN)
            self.state = 334
            self.expr()
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx

    class ExprContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(
            self, parser, parent: ParserRuleContext = None, invokingState: int = -1
        ):
            super().__init__(parent, invokingState)
            self.parser = parser

        def parts(self, i: int = None):
            if i is None:
                return self.getTypedRuleContexts(malParser.PartsContext)
            else:
                return self.getTypedRuleContext(malParser.PartsContext, i)

        def setop(self, i: int = None):
            if i is None:
                return self.getTypedRuleContexts(malParser.SetopContext)
            else:
                return self.getTypedRuleContext(malParser.SetopContext, i)

        def getRuleIndex(self):
            return malParser.RULE_expr

        def accept(self, visitor: ParseTreeVisitor):
            if hasattr(visitor, 'visitExpr'):
                return visitor.visitExpr(self)
            else:
                return visitor.visitChildren(self)

    def expr(self):
        localctx = malParser.ExprContext(self, self._ctx, self.state)
        self.enterRule(localctx, 68, self.RULE_expr)
        self._la = 0  # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 336
            self.parts()
            self.state = 342
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while ((_la) & ~0x3F) == 0 and ((1 << _la) & 60129542144) != 0:
                self.state = 337
                self.setop()
                self.state = 338
                self.parts()
                self.state = 344
                self._errHandler.sync(self)
                _la = self._input.LA(1)

        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx

    class PartsContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(
            self, parser, parent: ParserRuleContext = None, invokingState: int = -1
        ):
            super().__init__(parent, invokingState)
            self.parser = parser

        def part(self, i: int = None):
            if i is None:
                return self.getTypedRuleContexts(malParser.PartContext)
            else:
                return self.getTypedRuleContext(malParser.PartContext, i)

        def DOT(self, i: int = None):
            if i is None:
                return self.getTokens(malParser.DOT)
            else:
                return self.getToken(malParser.DOT, i)

        def getRuleIndex(self):
            return malParser.RULE_parts

        def accept(self, visitor: ParseTreeVisitor):
            if hasattr(visitor, 'visitParts'):
                return visitor.visitParts(self)
            else:
                return visitor.visitChildren(self)

    def parts(self):
        localctx = malParser.PartsContext(self, self._ctx, self.state)
        self.enterRule(localctx, 70, self.RULE_parts)
        self._la = 0  # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 345
            self.part()
            self.state = 350
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la == 37:
                self.state = 346
                self.match(malParser.DOT)
                self.state = 347
                self.part()
                self.state = 352
                self._errHandler.sync(self)
                _la = self._input.LA(1)

        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx

    class PartContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(
            self, parser, parent: ParserRuleContext = None, invokingState: int = -1
        ):
            super().__init__(parent, invokingState)
            self.parser = parser

        def LPAREN(self):
            return self.getToken(malParser.LPAREN, 0)

        def expr(self):
            return self.getTypedRuleContext(malParser.ExprContext, 0)

        def RPAREN(self):
            return self.getToken(malParser.RPAREN, 0)

        def varsubst(self):
            return self.getTypedRuleContext(malParser.VarsubstContext, 0)

        def ID(self):
            return self.getToken(malParser.ID, 0)

        def STAR(self):
            return self.getToken(malParser.STAR, 0)

        def type_(self, i: int = None):
            if i is None:
                return self.getTypedRuleContexts(malParser.TypeContext)
            else:
                return self.getTypedRuleContext(malParser.TypeContext, i)

        def getRuleIndex(self):
            return malParser.RULE_part

        def accept(self, visitor: ParseTreeVisitor):
            if hasattr(visitor, 'visitPart'):
                return visitor.visitPart(self)
            else:
                return visitor.visitChildren(self)

    def part(self):
        localctx = malParser.PartContext(self, self._ctx, self.state)
        self.enterRule(localctx, 72, self.RULE_part)
        self._la = 0  # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 362
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input, 35, self._ctx)
            if la_ == 1:
                self.state = 353
                self.match(malParser.LPAREN)
                self.state = 354
                self.expr()
                self.state = 355
                self.match(malParser.RPAREN)
                pass

            elif la_ == 2:
                self.state = 357
                self.varsubst()
                self.state = 358
                self.match(malParser.LPAREN)
                self.state = 359
                self.match(malParser.RPAREN)
                pass

            elif la_ == 3:
                self.state = 361
                self.match(malParser.ID)
                pass

            self.state = 365
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la == 30:
                self.state = 364
                self.match(malParser.STAR)

            self.state = 370
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la == 28:
                self.state = 367
                self.type_()
                self.state = 372
                self._errHandler.sync(self)
                _la = self._input.LA(1)

        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx

    class VarsubstContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(
            self, parser, parent: ParserRuleContext = None, invokingState: int = -1
        ):
            super().__init__(parent, invokingState)
            self.parser = parser

        def ID(self):
            return self.getToken(malParser.ID, 0)

        def getRuleIndex(self):
            return malParser.RULE_varsubst

        def accept(self, visitor: ParseTreeVisitor):
            if hasattr(visitor, 'visitVarsubst'):
                return visitor.visitVarsubst(self)
            else:
                return visitor.visitChildren(self)

    def varsubst(self):
        localctx = malParser.VarsubstContext(self, self._ctx, self.state)
        self.enterRule(localctx, 74, self.RULE_varsubst)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 373
            self.match(malParser.ID)
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx

    class TypeContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(
            self, parser, parent: ParserRuleContext = None, invokingState: int = -1
        ):
            super().__init__(parent, invokingState)
            self.parser = parser

        def LSQUARE(self):
            return self.getToken(malParser.LSQUARE, 0)

        def ID(self):
            return self.getToken(malParser.ID, 0)

        def RSQUARE(self):
            return self.getToken(malParser.RSQUARE, 0)

        def getRuleIndex(self):
            return malParser.RULE_type

        def accept(self, visitor: ParseTreeVisitor):
            if hasattr(visitor, 'visitType'):
                return visitor.visitType(self)
            else:
                return visitor.visitChildren(self)

    def type_(self):
        localctx = malParser.TypeContext(self, self._ctx, self.state)
        self.enterRule(localctx, 76, self.RULE_type)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 375
            self.match(malParser.LSQUARE)
            self.state = 376
            self.match(malParser.ID)
            self.state = 377
            self.match(malParser.RSQUARE)
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx

    class SetopContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(
            self, parser, parent: ParserRuleContext = None, invokingState: int = -1
        ):
            super().__init__(parent, invokingState)
            self.parser = parser

        def UNION(self):
            return self.getToken(malParser.UNION, 0)

        def INTERSECT(self):
            return self.getToken(malParser.INTERSECT, 0)

        def MINUS(self):
            return self.getToken(malParser.MINUS, 0)

        def getRuleIndex(self):
            return malParser.RULE_setop

        def accept(self, visitor: ParseTreeVisitor):
            if hasattr(visitor, 'visitSetop'):
                return visitor.visitSetop(self)
            else:
                return visitor.visitChildren(self)

    def setop(self):
        localctx = malParser.SetopContext(self, self._ctx, self.state)
        self.enterRule(localctx, 78, self.RULE_setop)
        self._la = 0  # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 379
            _la = self._input.LA(1)
            if not (((_la) & ~0x3F) == 0 and ((1 << _la) & 60129542144) != 0):
                self._errHandler.recoverInline(self)
            else:
                self._errHandler.reportMatch(self)
                self.consume()
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx

    class AssociationsContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(
            self, parser, parent: ParserRuleContext = None, invokingState: int = -1
        ):
            super().__init__(parent, invokingState)
            self.parser = parser

        def ASSOCIATIONS(self):
            return self.getToken(malParser.ASSOCIATIONS, 0)

        def LCURLY(self):
            return self.getToken(malParser.LCURLY, 0)

        def RCURLY(self):
            return self.getToken(malParser.RCURLY, 0)

        def association(self, i: int = None):
            if i is None:
                return self.getTypedRuleContexts(malParser.AssociationContext)
            else:
                return self.getTypedRuleContext(malParser.AssociationContext, i)

        def getRuleIndex(self):
            return malParser.RULE_associations

        def accept(self, visitor: ParseTreeVisitor):
            if hasattr(visitor, 'visitAssociations'):
                return visitor.visitAssociations(self)
            else:
                return visitor.visitChildren(self)

    def associations(self):
        localctx = malParser.AssociationsContext(self, self._ctx, self.state)
        self.enterRule(localctx, 80, self.RULE_associations)
        self._la = 0  # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 381
            self.match(malParser.ASSOCIATIONS)
            self.state = 382
            self.match(malParser.LCURLY)
            self.state = 386
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la == 19:
                self.state = 383
                self.association()
                self.state = 388
                self._errHandler.sync(self)
                _la = self._input.LA(1)

            self.state = 389
            self.match(malParser.RCURLY)
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx

    class AssociationContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(
            self, parser, parent: ParserRuleContext = None, invokingState: int = -1
        ):
            super().__init__(parent, invokingState)
            self.parser = parser

        def ID(self, i: int = None):
            if i is None:
                return self.getTokens(malParser.ID)
            else:
                return self.getToken(malParser.ID, i)

        def field(self, i: int = None):
            if i is None:
                return self.getTypedRuleContexts(malParser.FieldContext)
            else:
                return self.getTypedRuleContext(malParser.FieldContext, i)

        def mult(self, i: int = None):
            if i is None:
                return self.getTypedRuleContexts(malParser.MultContext)
            else:
                return self.getTypedRuleContext(malParser.MultContext, i)

        def LARROW(self):
            return self.getToken(malParser.LARROW, 0)

        def linkname(self):
            return self.getTypedRuleContext(malParser.LinknameContext, 0)

        def RARROW(self):
            return self.getToken(malParser.RARROW, 0)

        def meta(self, i: int = None):
            if i is None:
                return self.getTypedRuleContexts(malParser.MetaContext)
            else:
                return self.getTypedRuleContext(malParser.MetaContext, i)

        def getRuleIndex(self):
            return malParser.RULE_association

        def accept(self, visitor: ParseTreeVisitor):
            if hasattr(visitor, 'visitAssociation'):
                return visitor.visitAssociation(self)
            else:
                return visitor.visitChildren(self)

    def association(self):
        localctx = malParser.AssociationContext(self, self._ctx, self.state)
        self.enterRule(localctx, 82, self.RULE_association)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 391
            self.match(malParser.ID)
            self.state = 392
            self.field()
            self.state = 393
            self.mult()
            self.state = 394
            self.match(malParser.LARROW)
            self.state = 395
            self.linkname()
            self.state = 396
            self.match(malParser.RARROW)
            self.state = 397
            self.mult()
            self.state = 398
            self.field()
            self.state = 399
            self.match(malParser.ID)
            self.state = 403
            self._errHandler.sync(self)
            _alt = self._interp.adaptivePredict(self._input, 39, self._ctx)
            while _alt != 2 and _alt != ATN.INVALID_ALT_NUMBER:
                if _alt == 1:
                    self.state = 400
                    self.meta()
                self.state = 405
                self._errHandler.sync(self)
                _alt = self._interp.adaptivePredict(self._input, 39, self._ctx)

        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx

    class FieldContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(
            self, parser, parent: ParserRuleContext = None, invokingState: int = -1
        ):
            super().__init__(parent, invokingState)
            self.parser = parser

        def LSQUARE(self):
            return self.getToken(malParser.LSQUARE, 0)

        def ID(self):
            return self.getToken(malParser.ID, 0)

        def RSQUARE(self):
            return self.getToken(malParser.RSQUARE, 0)

        def getRuleIndex(self):
            return malParser.RULE_field

        def accept(self, visitor: ParseTreeVisitor):
            if hasattr(visitor, 'visitField'):
                return visitor.visitField(self)
            else:
                return visitor.visitChildren(self)

    def field(self):
        localctx = malParser.FieldContext(self, self._ctx, self.state)
        self.enterRule(localctx, 84, self.RULE_field)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 406
            self.match(malParser.LSQUARE)
            self.state = 407
            self.match(malParser.ID)
            self.state = 408
            self.match(malParser.RSQUARE)
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx

    class MultContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(
            self, parser, parent: ParserRuleContext = None, invokingState: int = -1
        ):
            super().__init__(parent, invokingState)
            self.parser = parser

        def multatom(self, i: int = None):
            if i is None:
                return self.getTypedRuleContexts(malParser.MultatomContext)
            else:
                return self.getTypedRuleContext(malParser.MultatomContext, i)

        def RANGE(self):
            return self.getToken(malParser.RANGE, 0)

        def getRuleIndex(self):
            return malParser.RULE_mult

        def accept(self, visitor: ParseTreeVisitor):
            if hasattr(visitor, 'visitMult'):
                return visitor.visitMult(self)
            else:
                return visitor.visitChildren(self)

    def mult(self):
        localctx = malParser.MultContext(self, self._ctx, self.state)
        self.enterRule(localctx, 86, self.RULE_mult)
        self._la = 0  # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 410
            self.multatom()
            self.state = 413
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la == 36:
                self.state = 411
                self.match(malParser.RANGE)
                self.state = 412
                self.multatom()

        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx

    class MultatomContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(
            self, parser, parent: ParserRuleContext = None, invokingState: int = -1
        ):
            super().__init__(parent, invokingState)
            self.parser = parser

        def INT(self):
            return self.getToken(malParser.INT, 0)

        def STAR(self):
            return self.getToken(malParser.STAR, 0)

        def getRuleIndex(self):
            return malParser.RULE_multatom

        def accept(self, visitor: ParseTreeVisitor):
            if hasattr(visitor, 'visitMultatom'):
                return visitor.visitMultatom(self)
            else:
                return visitor.visitChildren(self)

    def multatom(self):
        localctx = malParser.MultatomContext(self, self._ctx, self.state)
        self.enterRule(localctx, 88, self.RULE_multatom)
        self._la = 0  # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 415
            _la = self._input.LA(1)
            if not (_la == 13 or _la == 30):
                self._errHandler.recoverInline(self)
            else:
                self._errHandler.reportMatch(self)
                self.consume()
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx

    class LinknameContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(
            self, parser, parent: ParserRuleContext = None, invokingState: int = -1
        ):
            super().__init__(parent, invokingState)
            self.parser = parser

        def ID(self):
            return self.getToken(malParser.ID, 0)

        def getRuleIndex(self):
            return malParser.RULE_linkname

        def accept(self, visitor: ParseTreeVisitor):
            if hasattr(visitor, 'visitLinkname'):
                return visitor.visitLinkname(self)
            else:
                return visitor.visitChildren(self)

    def linkname(self):
        localctx = malParser.LinknameContext(self, self._ctx, self.state)
        self.enterRule(localctx, 90, self.RULE_linkname)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 417
            self.match(malParser.ID)
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx
