from dataclasses import dataclass
from typing import Sequence, Union, List
import re

@dataclass
class Operand:
    name: str
    
    def __repr__(self):
        return f"Operand({self.name})"

@dataclass
class Operation:
    name: str
    operands: Sequence[Union["Operand", "Operation"]]
    
    def __repr__(self):
        return f"Operation({self.name}, {list(self.operands)})"

@dataclass
class Rule:
    name: str
    original: Union[Operation, Operand]
    rewritten: Union[Operation, Operand]
    
    def __repr__(self):
        return f"Rule({self.name}, {self.original} -> {self.rewritten})"

@dataclass
class RuleSet:
    name: str
    rules: List[Rule]
    
    def __repr__(self):
        return f"RuleSet({self.name}, {len(self.rules)} rules)"

class SExpressionParser:
    def __init__(self, text: str):
        self.tokens = self._tokenize(text)
        self.pos = 0
    
    def _tokenize(self, text: str) -> List[str]:
        # Remove comments
        text = re.sub(r';[^\n]*', '', text)
        # Split on all delimiters (parentheses, brackets, whitespace), keeping delimiters
        tokens = re.findall(r'[()[\]]|[^\s()[\]]+', text)
        return [t for t in tokens if t.strip()]
    
    def _peek(self) -> str:
        if self.pos >= len(self.tokens):
            return ''
        return self.tokens[self.pos]
    
    def _consume(self) -> str:
        if self.pos >= len(self.tokens):
            raise ValueError("Unexpected end of input")
        token = self.tokens[self.pos]
        self.pos += 1
        return token
    
    def _parse_expression(self) -> Union[Operation, Operand]:
        if self._peek() == '(':
            return self._parse_operation()
        else:
            return self._parse_operand()
    
    def _parse_operand(self) -> Operand:
        name = self._consume()
        return Operand(name)
    
    def _parse_operation(self) -> Operation:
        self._consume()  # consume '('
        
        if self.pos >= len(self.tokens):
            raise ValueError("Unexpected end of input in operation")
        
        name = self._consume()
        operands = []
        
        while self._peek() != ')':
            if not self._peek():
                raise ValueError("Unclosed operation")
            operands.append(self._parse_expression())
        
        self._consume()  # consume ')'
        return Operation(name, operands)
    
    def _parse_rule(self) -> Rule:
        self._consume()  # consume '['
        
        rule_name = self._consume()
        original = self._parse_expression()
        rewritten = self._parse_expression()
        
        if self._peek() != ']':
            raise ValueError(f"Expected ']' after rule {rule_name}")
        self._consume()  # consume ']'
        
        return Rule(rule_name, original, rewritten)
    
    def _parse_rule_set(self) -> RuleSet:
        self._consume()  # consume '('
        
        if self._consume() != 'define-rules':
            raise ValueError("Expected 'define-rules'")
        
        name = self._consume()
        rules = []
        
        while self._peek() != ')':
            if not self._peek():
                raise ValueError("Unclosed rule set")
            if self._peek() == '[':
                rules.append(self._parse_rule())
            else:
                raise ValueError(f"Expected '[' for rule, got '{self._peek()}'")
        
        self._consume()  # consume ')'
        return RuleSet(name, rules)
    
    def parse(self) -> List[RuleSet]:
        rule_sets = []
        while self.pos < len(self.tokens):
            if self._peek() == '(':
                rule_sets.append(self._parse_rule_set())
            else:
                raise ValueError(f"Expected '(' at top level, got '{self._peek()}'")
        return rule_sets

# Example usage:
def parse_rewrite_rules(text: str) -> List[RuleSet]:
    parser = SExpressionParser(text)
    return parser.parse()

# Test with your example:
if __name__ == "__main__":
    example_text = """
    (define-rules arithmetic
      [sub-flip (- a b) (+ a (neg b))]
      [sub-flip-reverse (+ a (neg b)) (- a b)]
      [sub-negate (neg (- b a)) (- a b)]
      [sub-negate-rev (- a b) (neg (- b a))]
      [add-flip (+ a b) (- a (neg b))]
      [add-flip-rev (- a (neg b)) (+ a b)])

    ; Difference of squares
    (define-rules polynomials
      [swap-sqr (* (* a b) (* a b)) (* (* a a) (* b b))]
      [unswap-sqr (* (* a a) (* b b)) (* (* a b) (* a b))]
      [difference-of-squares (- (* a a) (* b b)) (* (+ a b) (- a b))]
      [difference-of-sqr-1 (- (* a a) 1) (* (+ a 1) (- a 1))])
    """
    
    rule_sets = parse_rewrite_rules(example_text)
    
    for rule_set in rule_sets:
        print(f"\nRuleSet: {rule_set.name}")
        for rule in rule_set.rules:
            print(f"  {rule.name}: {rule.original} -> {rule.rewritten}")
