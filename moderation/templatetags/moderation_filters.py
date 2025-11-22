from django import template

register = template.Library()

@register.filter
def score_color(score):
    """Return a Bootstrap color class based on score severity."""
    try:
        # Convert to float if it's a string
        score_float = float(score) if isinstance(score, str) else score
        if score_float >= 0.7:
            return 'danger'
        elif score_float >= 0.4:
            return 'warning'
        return 'success'
    except (ValueError, TypeError):
        # Return a default color if conversion fails
        return 'secondary'

@register.filter
def safe_score_color(score):
    """Return a Bootstrap color class for safety score (inverse of severity)."""
    if score >= 0.7:
        return 'success'
    elif score >= 0.4:
        return 'warning'
    return 'danger'

@register.filter
def multiply(value, arg):
    """Multiply the value by the arg."""
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return 0

@register.filter
def get_item(dictionary, key):
    """Get a value from a dictionary by key."""
    return dictionary.get(key)
