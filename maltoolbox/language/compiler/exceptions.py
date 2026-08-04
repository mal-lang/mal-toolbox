class MalCompilerError(Exception):
    """Base exception for MalCompiler errors."""



class MalSyntaxError(MalCompilerError):
    """Raised when syntax error is encountered during compilation."""

    def __init__(self, message, line=None, column=None):
        self.line = line
        self.column = column
        super().__init__(message)


class MalParseError(MalCompilerError):
    """Raised when parsing fails."""



class MalTypeError(MalCompilerError):
    """Raised when type checking fails."""



class MalNameError(MalCompilerError):
    """Raised when an undefined name is referenced."""



class MalCompilationError(MalCompilerError):
    """Raised when code generation fails."""

