"""Stub MongoDB connector — we don't actually use MongoDB in this demo.
Only needed because read.py / optimize.py import it at top level.
Anything that touches the real collections will raise NotImplementedError.
"""
class _StubCollection:
    def __getattr__(self, _): raise NotImplementedError("MongoDB is stubbed in this demo")

collection_calculation = _StubCollection()
collection_system      = _StubCollection()
db                     = _StubCollection()
