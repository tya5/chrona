# Implementation Amendment — Single Schema Diagnostic Compatibility (#450)

Retain the original `explain_errors` implementation.  Add and test
`explain_all_errors` separately, including union leaf flattening; make no
existing caller switch until I450-2's collector is introduced.
