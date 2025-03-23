"""
Utility functions for converting between snake_case and camelCase.

This module provides functions to convert dictionary keys between different case conventions,
particularly useful for API responses where the backend uses snake_case (Python convention)
but the frontend expects camelCase (JavaScript convention).
"""


def to_camel_case(snake_str):
    """Convert a snake_case string to camelCase.

    Args:
        snake_str: A string in snake_case format

    Returns:
        The string converted to camelCase
    """
    components = snake_str.split("_")
    return components[0] + "".join(x.title() for x in components[1:])


def snake_to_camel_dict(d):
    """Recursively convert all keys in a dictionary from snake_case to camelCase.

    Args:
        d: A dictionary or other data structure that may contain dictionaries

    Returns:
        A new dictionary with all keys converted from snake_case to camelCase
    """
    if not isinstance(d, dict):
        return d

    result = {}
    for key, value in d.items():
        # Skip keys that start with underscore (private attributes)
        if isinstance(key, str) and not key.startswith("_"):
            camel_key = to_camel_case(key)

            # Handle nested dictionaries and lists
            if isinstance(value, dict):
                result[camel_key] = snake_to_camel_dict(value)
            elif isinstance(value, list):
                result[camel_key] = [
                    snake_to_camel_dict(item) if isinstance(item, dict) else item
                    for item in value
                ]
            else:
                result[camel_key] = value
        else:
            # Keep the key as is if it's not a string or starts with underscore
            result[key] = value

    return result


def to_snake_case(camel_str):
    """Convert a camelCase string to snake_case.

    Args:
        camel_str: A string in camelCase format

    Returns:
        The string converted to snake_case
    """
    result = [camel_str[0].lower()]
    for char in camel_str[1:]:
        if char.isupper():
            result.append("_")
            result.append(char.lower())
        else:
            result.append(char)
    return "".join(result)


def camel_to_snake_dict(d):
    """Recursively convert all keys in a dictionary from camelCase to snake_case.

    Args:
        d: A dictionary or other data structure that may contain dictionaries

    Returns:
        A new dictionary with all keys converted from camelCase to snake_case
    """
    if not isinstance(d, dict):
        return d

    result = {}
    for key, value in d.items():
        # Skip keys that start with underscore (private attributes)
        if isinstance(key, str) and not key.startswith("_"):
            snake_key = to_snake_case(key)

            # Handle nested dictionaries and lists
            if isinstance(value, dict):
                result[snake_key] = camel_to_snake_dict(value)
            elif isinstance(value, list):
                result[snake_key] = [
                    camel_to_snake_dict(item) if isinstance(item, dict) else item
                    for item in value
                ]
            else:
                result[snake_key] = value
        else:
            # Keep the key as is if it's not a string or starts with underscore
            result[key] = value

    return result
