from dataclasses import dataclass
from typing import Sequence

@dataclass
class Operand:
    name: str

@dataclass
class Operation:
    name: str
    operands: Sequence["Operand|Operation"]

@dataclass
class Rule:
    name: str
    original: Operation|Operand
    rewritten: Operation|Operand

def convert_rule():
    ...


if __name__ == "__main__":
    print("hello world")
