grammar Mcd;

program        : cloudAppDecl EOF ;
cloudAppDecl   : 'cloud' 'app' STRING '{' resourceDecl* '}' ;
resourceDecl   : networkDecl | subnetDecl | computeDecl | storageDecl | firewallDecl | varDecl | unsupportedDecl ;
networkDecl    : 'network' STRING '{' attribute* '}' ;
subnetDecl     : 'subnet' STRING '{' attribute* '}' ;
computeDecl    : 'compute' STRING '{' attribute* '}' ;
storageDecl    : 'storage' STRING '{' attribute* '}' ;
firewallDecl   : 'firewall' STRING '{' attribute* '}' ;
unsupportedDecl: IDENT STRING '{' attribute* '}' ;
varDecl        : 'var' IDENT '=' literal ';' ;
attribute      : IDENT '=' value ';'? ;
value          : literal | list | object | interpolatedRef ;
list           : '[' (value (',' value)*)? ']' ;
object         : '{' (IDENT '=' value (',' IDENT '=' value)*)? '}' ;
literal        : STRING | INT | BOOL ;
interpolatedRef: '${' IDENT '}' ;

BOOL: 'true' | 'false';
STRING: '"' (~["\\] | '\\' .)* '"';
INT: [0-9]+;
IDENT: [A-Za-z_][A-Za-z0-9_-]*;
LINE_COMMENT: '//' ~[\r\n]* -> skip;
BLOCK_COMMENT: '/*' .*? '*/' -> skip;
WS: [ \t\r\n]+ -> skip;
