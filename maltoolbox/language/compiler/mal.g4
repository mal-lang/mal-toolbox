grammar mal;

mal: (declaration)+ | EOF;

declaration: include
           | define
           | category
           | associations;

include: INCLUDE STRING;

define: HASH ID COLON STRING; // TODO version and id are mandatory

category: CATEGORY ID meta* LCURLY asset* RCURLY;
meta: ID INFO COLON text;
text: STRING | MULTILINE_STRING;
asset: ABSTRACT? ASSET ID (EXTENDS ID)? meta* LCURLY (step|variable)* RCURLY;

step: steptype ID tag* cias? pdist? meta* detector* precondition? reaches?;
steptype: AND | OR | HASH | EXISTS | NOTEXISTS;
tag: AT ID;
cias: LCURLY cia (COMMA cia)* RCURLY;
cia: C|I|A;
ttc: pdist;
pdist: LSQUARE pdistexpr RSQUARE;
pdistexpr: pdistterm ((PLUS | MINUS) pdistterm)*;
pdistterm: pdistfact ((STAR | DIVIDE) pdistfact)*;
pdistfact: pdistatom (POWER pdistatom)?;
pdistatom: pdistdist | LPAREN pdistexpr RPAREN | number;
pdistdist: ID (LPAREN (number (COMMA number)*)? RPAREN)?;
detector: bang detectorname? context detectortype? tprate?;
bang: EXCLAMATION | EXCLM_COMM;
detectorname: ID (DOT ID)*;
context: LPAREN contextpart (COMMA contextpart)* RPAREN;
contextpart: contextasset contextlabel;
contextasset: ID;
contextlabel: ID;
detectortype: ID;
tprate: pdist;
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
STRING: '"' ( ~["\\\r\n] | '\\' . )* '"';
MULTILINE_STRING: '"""' ( '"'? '"'? ~["] | '\n' | '\r' )* '"""';

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
EXCLAMATION: '!';
NOTEXISTS: '!E';
AT: '@';
REQUIRES: '<-';
INHERITS: '+>';
LEADSTO: '->';
COMMA: ',';
PLUS: '+';
DIVIDE: '/';
POWER: '^';
EXCLM_COMM: '//!';


// garbage
INLINE_COMMENT: '//' ~[!]~[\r\n]* -> skip;
MULTILINE_COMMENT: '/*' .*? '*/' -> skip;
WS: [ \t\r\n] -> skip;
