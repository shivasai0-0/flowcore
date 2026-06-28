import logging
from typing import Any, Callable, Dict
from src.schemas.graph import EdgeCondition
from src.schemas.carry_unit import CarryUnit
from src.modules.base import get_carry_unit_field

logger = logging.getLogger("flowcore.conditions")

ConditionOperator = Callable[[EdgeCondition, str, CarryUnit], bool]

def always_operator(cond: EdgeCondition, user_input: str, carry_unit: CarryUnit) -> bool:
    return True

def any_input_operator(cond: EdgeCondition, user_input: str, carry_unit: CarryUnit) -> bool:
    return len(user_input.strip()) > 0

def input_equals_operator(cond: EdgeCondition, user_input: str, carry_unit: CarryUnit) -> bool:
    if cond.value is None:
        raise ValueError("input_equals condition requires a non-null 'value'")
    from src.engine.actions import get_action_for_input
    user_action = get_action_for_input(user_input)
    cond_action = get_action_for_input(str(cond.value))
    if user_action and cond_action and user_action == cond_action:
        return True
    if user_action and user_action.strip().lower() == str(cond.value).strip().lower():
        return True
    return user_input.strip().lower() == str(cond.value).strip().lower()

def input_in_operator(cond: EdgeCondition, user_input: str, carry_unit: CarryUnit) -> bool:
    if not isinstance(cond.value, list):
        raise ValueError(f"input_in condition expects a list for value, got: {type(cond.value)}")
    vals = [str(v).strip().lower() for v in cond.value]
    from src.engine.actions import get_action_for_input
    user_action = get_action_for_input(user_input)
    if user_action:
        if user_action.strip().lower() in vals:
            return True
        for val in cond.value:
            cond_action = get_action_for_input(str(val))
            if cond_action and user_action == cond_action:
                return True
    return user_input.strip().lower() in vals

def carry_equals_operator(cond: EdgeCondition, user_input: str, carry_unit: CarryUnit) -> bool:
    if not cond.key:
        raise ValueError("carry_equals condition is missing required 'key'")
    if cond.value is None:
        raise ValueError("carry_equals condition is missing required 'value'")
    val = get_carry_unit_field(carry_unit, cond.key)
    return str(val).lower() == str(cond.value).strip().lower()

def carry_greater_than_operator(cond: EdgeCondition, user_input: str, carry_unit: CarryUnit) -> bool:
    if not cond.key:
        raise ValueError("carry_greater_than condition is missing required 'key'")
    if cond.value is None:
        raise ValueError("carry_greater_than condition is missing required 'value'")
    val = get_carry_unit_field(carry_unit, cond.key)
    try:
        return float(val) > float(cond.value)
    except (ValueError, TypeError) as e:
        logger.error(f"Numeric comparison failed for key '{cond.key}' (value: '{val}') and cond.value '{cond.value}': {str(e)}")
        raise ValueError(f"Numeric comparison failed: key '{cond.key}' (value: '{val}') is not numeric.")

# Registry mapping condition types to operator functions
OPERATORS: Dict[str, ConditionOperator] = {
    "always": always_operator,
    "any_input": any_input_operator,
    "input_equals": input_equals_operator,
    "input_in": input_in_operator,
    "carry_equals": carry_equals_operator,
    "carry_greater_than": carry_greater_than_operator
}

def evaluate_condition(cond: EdgeCondition, user_input: str, carry_unit: CarryUnit) -> bool:
    """Evaluates whether an edge transition condition is met via the registry."""
    op = OPERATORS.get(cond.type)
    if not op:
        logger.error(f"Unsupported condition type: '{cond.type}'")
        raise ValueError(f"Unsupported condition type: '{cond.type}'")
    try:
        res = op(cond, user_input, carry_unit)
        logger.info(f"Condition type='{cond.type}' key='{cond.key}' value='{cond.value}' against input='{user_input}' evaluated to {res}")
        return res
    except Exception as e:
        logger.error(f"Failed to evaluate condition type='{cond.type}' key='{cond.key}': {str(e)}")
        raise
