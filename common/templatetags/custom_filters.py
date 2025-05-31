from django import template
from datetime import datetime
import locale
from common.utils import get_currency_symbol

register = template.Library()

@register.filter
def time_format(value):
    if isinstance(value, str):
        try:
            # Try to convert string to time object
            value = datetime.strptime(value, '%H:%M:%S').time()
        except ValueError:
            return value  # If parsing fails, return the original value
    return value.strftime('%-I:%M%p').lower()

@register.filter
def truncate_words_chars(value):
    words = value.split()
    truncated = ' '.join(words[:2])  # Take first two words
    if len(truncated) > 13:
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

@register.filter
def custom_comma_format(value):
    try:
        """Set locale to format with commas"""
        locale.setlocale(locale.LC_ALL, 'en_US.UTF-8')
        formatted_value = locale.format_string("%.2f", value, grouping=True)
        return formatted_value
    except (ValueError, TypeError):
        return value
    
@register.filter
def currency_symbol(currency_code):
    return get_currency_symbol(currency_code)


@register.filter
def get_item(dictionary, key):
    """Retrieve a value from a dictionary using a key."""
    return dictionary.get(key, "")

@register.filter
def mul(value, arg):
    """Multiply two numbers."""
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return ''