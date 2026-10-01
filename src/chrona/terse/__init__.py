"""The terse plan syntax: a text front end that compiles to a `timeline/v0.7` Project (Spec 65).

Imports only `chrona.core`. No I/O: it takes text and returns a value. Reached from adapters through
`chrona.usecases.terse_compile`.
"""
from chrona.terse.compiler import CompileResult, SourceMap, compile_terse, locate
from chrona.terse.diagnostics import CODES, SourceRange, TerseDiagnostic
from chrona.terse.emitter import HEADER, emit_project
from chrona.terse.ledger import LEDGER
from chrona.terse.lexer import decode

__all__ = ("CODES", "HEADER", "LEDGER", "CompileResult", "SourceMap", "SourceRange", "TerseDiagnostic",
           "compile_terse", "decode", "emit_project", "locate")
