from django import template

register = template.Library()

@register.filter
def time_format(value):
    return value.strftime('%-I:%M%p').lower()

@register.filter
def truncate_words_chars(value):
    words = value.split()
    truncated = ' '.join(words[:2])  # Take first two words
    if len(truncated) > 22:
        truncated = truncated[:12] + '...'  # Limit to 12 characters
    return truncated

@register.filter
def get(dictionary, key):
    """Get value from dictionary for the given key."""
    if isinstance(dictionary, dict):
        return dictionary.get(key)
    return None  

@register.filter
def format_expense_type(value):
    """Replace underscores with spaces and capitalize each word."""
    return value.replace('_', ' ').title()