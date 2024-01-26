grammar mal;

mal: (declaration)+ | EOF;

declaration: include
           | define
           | category
           | associations;

include: INCLUDE STRING;

define: HASH ID COLON STRING; // TODO version and id are mandatory

category: CATEGORY ID meta* LCURLY asset* RCURLY;
meta: ID INFO COLON STRING;
asset: ABSTRACT? ASSET ID (EXTENDS ID)? meta* LCURLY (step|variable)* RCURLY;

step: steptype ID tag* cias? ttc? meta* precondition? reaches?;
steptype: AND | OR | HASH | EXISTS | NOTEXISTS;
tag: AT ID;
cias: LCURLY cia (COMMA cia)* RCURLY;
cia: C|I|A;
ttc: LSQUARE ttcexpr RSQUARE;
ttcexpr: ttcterm ((PLUS | MINUS) ttcterm)*;
ttcterm: ttcfact ((STAR | DIVIDE) ttcfact)*;
ttcfact: ttcatom (POWER ttcatom)?;
ttcatom: ttcdist | LPAREN ttcexpr RPAREN | number;
ttcdist: ID (LPAREN (number (COMMA number)*)? RPAREN)?;
precondition: REQUIRES expr (COMMA expr)*;
reaches: (INHERITS | LEADSTO) expr (COMMA expr)*;
number: INT | FLOAT;  // defined as rule, otherwise it would conflict with INT/FLOAT tokens

variable: LET ID ASSIGN expr;

// Example of valid expression:
// a.b.(c \/ d).(e[4] /\ f[6])*[6] \/ g
expr: parts (setop parts)*;
parts: part (DOT part)*;
part: (LPAREN expr RPAREN | varsubst LPAREN RPAREN | ID) STAR? type*;
varsubst: ID;
type: LSQUARE ID RSQUARE;
setop: UNION | INTERSECT | MINUS;

associations: ASSOCIATIONS LCURLY association* RCURLY;
association: ID field mult LARROW linkname RARROW mult field ID meta*;
field: LSQUARE ID RSQUARE;
mult: multatom (RANGE multatom)?;
multatom: INT | STAR;
linkname: ID;


// TOKENS

// words
ABSTRACT: 'abstract';
ASSET: 'asset';
ASSOCIATIONS: 'associations';
EXTENDS: 'extends';
INCLUDE: 'include';
CATEGORY: 'category';
INFO: 'info';
LET: 'let';

// patterns
STRING: '"' .*? '"';
INT: [0-9]+;
FLOAT: [0-9]* DOT [0-9]+;
EXISTS: 'E';  //
C: 'C';       //
I: 'I';       // chars but defined here to take precedence over ID
A: 'A';       //
ID: [a-zA-Z0-9_]+;

// chars / symbols
LPAREN: '(';
RPAREN: ')';
LCURLY: '{';
RCURLY: '}';
HASH: '#';
COLON: ':';
LARROW: '<--';
RARROW: '-->';
LSQUARE: '[';
RSQUARE: ']';
STAR: '*';
ONE: '1';
ASSIGN: '=';
MINUS: '-';
INTERSECT: '/\\';
UNION: '\\/';
RANGE: '..';
DOT: '.';
AND: '&';
OR: '|';
NOTEXISTS: '!E';
AT: '@';
REQUIRES: '<-';
INHERITS: '+>';
LEADSTO: '->';
COMMA: ',';
PLUS: '+';
DIVIDE: '/';
POWER: '^';


// garbage
INLINE_COMMENT: '//' ~[\r\n]* -> skip;
MULTILINE_COMMENT: '/*' .*? '*/' -> skip;
WS: [ \t\r\n] -> skip;

