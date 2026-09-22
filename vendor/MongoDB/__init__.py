"""Stub MongoDB 包,仅为了让 PCT_Toolkit/src/read.py 的顶层 import 通过。

官方代码里 `from MongoDB.connect import ...` 在 read 顶部就会执行,但
我们的 wrapper 完全不用 MongoDB。这里创建一个空模块树占位。
"""

def _stub(name):
    """生成一个 stub 属性访问,任何属性都返回空/0/list."""
    class _Anything:
        def __getattr__(self, k): return _Anything()
        def __call__(self, *a, **k): return _Anything()
        def __iter__(self): return iter([])
        def __bool__(self): return False
    return _Anything()

import sys, types

pkg = types.ModuleType("MongoDB")
pkg.__path__ = []  # 标记为包
sys.modules["MongoDB"] = pkg

connect = types.ModuleType("MongoDB.connect")
connect.collection_calculation = _stub("collection_calculation")
connect.collection_system = _stub("collection_system")
connect.db = _stub("db")
sys.modules["MongoDB.connect"] = connect
