from django import template
from django.urls import reverse

register = template.Library()


@register.inclusion_tag('common/audit_tag_row.html')
def audit_tag_row(created_by, last_modified_by, app_label, model_name, object_id, size=''):
    """Pass size='small' to wrap tags in &lt;small&gt; (matches shuttle list styling)."""
    return {
        'created_by': created_by,
        'last_modified_by': last_modified_by,
        'audit_url': reverse(
            'common:audit_detail',
            kwargs={'app_label': app_label, 'model_name': model_name, 'pk': object_id},
        ),
        'use_small': size == 'small',
    }
