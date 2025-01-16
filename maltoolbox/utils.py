import operator
from dataclasses import dataclass
from typing import Any, Dict, TypeVar

K = TypeVar("K")
V = TypeVar("V")

class LookupDict(Dict[K, V]):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._indices = {}

    def __setitem__(self, key, value):
        super().__setitem__(key, value)
        self._indices.clear()

    def __delitem__(self, key):
        super().__delitem__(key)
        self._indices.clear()

    def lookup(self, key: str, value: Any, op: str ="eq") -> set[Any]:
        if key not in self._indices:
            self._indices[key] = {getattr(v, key): set() for v in self.values()}
            for v in self.values():
                if not (vkey:=getattr(v, key)) in self._indices[key].keys():
                    self._indices[key][vkey] = set()

                self._indices[key][vkey].add(v)

        if op == "eq":
            try:
                return self._indices[key][value]
            except KeyError:
                return set()

        if op == "in":
            oper = lambda a, b: operator.contains(b, a)
        else:
            try:
                oper = getattr(operator, op)
            except AttributeError:
                raise ValueError(f"Invalid operator {op}")

        ret = set()
        for i in filter(lambda k: oper(k, value), self._indices[key]):
            ret.update(self._indices[key][i])

        return ret

    def fetch(self, key: str, value: Any, op: str="eq") -> Any:
        ret = self.lookup(key, value, op)

        if len(ret) > 1:
            raise ValueError(f"Multiple items match {key} ~ {op} ~ {value}")

        try:
            return next(iter(ret))
        except KeyError:
            return None

@dataclass
class Asset:
    id: int
    name: str
    props: list
    def __hash__(self):
        return self.name


class Test:
    def __init__(self):
        self.assets = LookupDict({
                "one": Asset("one", 1, [0,1,2]), "two": Asset("two", 2,
                                                              [1,2,3]), "three":
                Asset("thre", 3, [2,3,4])})

t=Test()
t.assets.lookup('name', 'one')
t.assets["four"] = Asset("four",4, [3,4,5])
t.assets.lookup('name', 'four')
