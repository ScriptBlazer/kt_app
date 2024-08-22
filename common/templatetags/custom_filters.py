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