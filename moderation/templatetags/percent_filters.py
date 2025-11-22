from django import template

register = template.Library()

@register.filter
def to_percent(value, decimals=0):
    """Converts a float 0-1 to percentage 0-100"""
    try:
        return round(float(value) * 100, int(decimals))
    except (ValueError, TypeError):
        return 0

@register.filter
def sub(value, arg):
    """Subtracts the argument from the value"""
    try:
        return float(value) - float(arg)
    except (ValueError, TypeError):
        return 0
