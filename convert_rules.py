from typing import Dict, Union
from xdsl.builder import Builder
from xdsl.dialects import pdl
from xdsl.dialects.builtin import AnyFloat, AnySignlessIntegerType, IntegerAttr, IntegerType, StringAttr, ArrayAttr, f32, FloatAttr
from xdsl.ir import SSAValue
from xdsl.ir.core import OpResult

from parse import Rule, Operation, Operand, Literal

operation_map = {
    # Basic Arithmetic (arith dialect)
    '+': 'arith.addf',
    '-': 'arith.subf',
    '*': 'arith.mulf',
    '/': 'arith.divf',
    'remainder': 'arith.remf',
    'neg': 'arith.negf',

    # Math Functions (math dialect)
    'fabs': 'math.absf',
    'copysign': 'math.copysign',
    'pow': 'math.powf',
    'sqrt': 'math.sqrt',
    'cbrt': 'math.cbrt',
    'log': 'math.log',
    'exp': 'math.exp',
    'sin': 'math.sin',
    'cos': 'math.cos',
    'tan': 'math.tan',
    'asin': 'math.asin',
    'acos': 'math.acos',
    'atan': 'math.atan',
    'atan2': 'math.atan2',
    'sinh': 'math.sinh',
    'cosh': 'math.cosh',
    'tanh': 'math.tanh',
    'asinh': 'math.asinh',
    'acosh': 'math.acosh',
    'atanh': 'math.atanh',
}

def convert_rule_to_pdl_pattern(
    rule: Rule, 
    operation_mapping: Dict[str, str] = operation_map,
    element_type: Union[AnyFloat, AnySignlessIntegerType] = f32,
    benefit: int = 1
) -> pdl.PatternOp:
    """
    Convert a Rule to a PDL PatternOp.
    
    Args:
        rule: The rewrite rule to convert
        operation_mapping: Maps operation names to MLIR operation names (e.g., "+" -> "arith.addi")
        element_type: The common type for all operands/results (default: i32)
        benefit: Pattern benefit/priority (default: 1)
    """
    
    # Track PDL values for operands and intermediate results
    pdl_values: Dict[str, SSAValue] = {}
    
    @Builder.implicit_region
    def pattern_body() -> None:
        # Create a common type
        common_type = pdl.TypeOp(element_type)
        typevar = common_type.result
        
        # Create PDL operands for all variables in the rule
        for operand_name in rule.operands:
            operand = pdl.OperandOp(typevar)
            pdl_values[operand_name] = operand.value
        
        # Build the original pattern (left-hand side)
        root_value = _build_expression(rule.original, pdl_values, element_type, typevar, operation_mapping)
        assert isinstance(root_value, OpResult)
        assert isinstance(root_value.owner, pdl.ResultOp)
        root_op = root_value.owner.parent_
        
        # Create the rewrite region
        @Builder.implicit_region  
        def rewrite_body() -> None:
            # Build the replacement (right-hand side)
            replacement = _build_expression(rule.rewritten, pdl_values, element_type, typevar, operation_mapping)
            
            pdl.ReplaceOp(op_value=root_op, repl_values=[replacement])
        
        # Create the rewrite operation
        pdl.RewriteOp(root=root_op, body=rewrite_body)
    
    # Create the pattern
    pattern = pdl.PatternOp(benefit, _sanitize_rulename(rule.name), pattern_body)
    return pattern
    
def _sanitize_rulename(name: str):
    sanitized = (
            name
            .replace('--', 'sub_')
            .replace('+', 'add')
            .replace('*', 'mul')
            .replace('/', 'div')
            .replace('-', '_')  # if you meant hyphens to become underscores
        )
    if sanitized[0].isdigit():
        sanitized = "_" + sanitized
    return sanitized
    
def _build_expression(
    expr: Union[Operation, Operand, Literal],
    pdl_values: Dict[str, SSAValue],
    element_type: Union[AnyFloat, IntegerType],
    typevar: OpResult[pdl.TypeType], 
    operation_mapping: Dict[str, str]
) -> SSAValue:
    """
    Build a PDL expression from an Operation/Operand/Literal.
    
    Returns:
        SSAValue for operands and operation results
        tuple('operation', SSAValue) for operations in rewrite context
    """
    
    if isinstance(expr, Operand):
        # Return existing operand value
        return pdl_values[expr.name]
    
    elif isinstance(expr, Literal):
        # Create arith.constant operation with the literal value
        # First create the attribute containing the value
        if isinstance(element_type, IntegerType):
            assert isinstance(expr.value, int)
            attr = pdl.AttributeOp(IntegerAttr(expr.value, element_type))
        elif isinstance(element_type, AnyFloat):
            assert isinstance(element_type, AnyFloat)
            attr = pdl.AttributeOp(FloatAttr(expr.value, element_type))
        else:
            raise ValueError(f"Unsupported literal type: {type(expr.value)}")
        
        # Create arith.constant operation
        const_op = pdl.OperationOp(
            op_name="arith.constant",
            attribute_value_names=ArrayAttr([StringAttr("value")]),
            attribute_values=(attr.output,),
            type_values=(typevar,)
        )
        
        # Return the first result of the constant operation
        result = pdl.ResultOp(IntegerAttr.from_int_and_width(0, 32), const_op.results[0])
        return result.val
    
    elif isinstance(expr, Operation):
        # Map the operation name using the operation_mapping
        if expr.name not in operation_mapping:
            raise ValueError(f"Unknown operation: {expr.name}")
        
        mlir_op_name = operation_mapping[expr.name]
        
        # Build operands recursively
        operand_values = []
        for operand in expr.operands:
            operand_val = _build_expression(operand, pdl_values, element_type, typevar, operation_mapping)
            # If it's a tuple (operation result), extract the value
            if isinstance(operand_val, tuple):
                operand_val = operand_val[1]
            operand_values.append(operand_val)
        
        # Create the operation
        op = pdl.OperationOp(
            op_name=mlir_op_name,
            operand_values=operand_values,
            type_values=(typevar,)
        )
        
        # Return the operation result
        result = pdl.ResultOp(IntegerAttr.from_int_and_width(0, 32), op.results[0])
        return result.val
    
    else:
        raise ValueError(f"Unsupported expression type: {type(expr)}")

    
if __name__ == "__main__":
    # Create a simple rule: x + y -> y + x
    rule = Rule(
        name="commutativity",
        original=Operation("+", (Operand("x"), Operand("y"))),
        rewritten=Operation("+", (Operand("y"), Operand("x"))),
        operands={"x", "y"}
    )
    
    # Convert to PDL pattern
    pattern = convert_rule_to_pdl_pattern(
        rule, 
        operation_map,
        element_type=f32,
        benefit=2
    )
    print(pattern)
