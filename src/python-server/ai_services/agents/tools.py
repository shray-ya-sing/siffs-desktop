from langchain.tools import tool

@tool
def add(a: int, b: int) -> int:
    """Adds two integers together.
    
    Args:
        a: First integer
        b: Second integer
        
    Returns:
        The sum of a and b
    """
    return a + b

@tool
def multiply(a: int, b: int) -> int:
    """Multiplies two integers together.
    
    Args:
        a: First integer
        b: Second integer
        
    Returns:
        The product of a and b
    """
    return a * b

@tool
def divide(a: int, b: int) -> float:
    """Divides first integer by the second.
    
    Args:
        a: The numerator
        b: The denominator (must not be zero)
        
    Returns:
        The result of a divided by b as a float
    """
    if b == 0:
        raise ValueError("Cannot divide by zero")
    return a / b

# Export all tools in a list for easy importing
ALL_TOOLS = [add, multiply, divide]
