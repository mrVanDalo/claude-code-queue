#!/usr/bin/env python3

def greet(name):
    """Greet someone by name."""
    return f"Hello, {name}!"

def calculate_square(number):
    """Calculate the square of a number."""
    return number ** 2

if __name__ == "__main__":
    print(greet("Claude Code Queue"))
    print(f"Square of 7 is: {calculate_square(7)}")