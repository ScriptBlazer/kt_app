from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from analytics.models import JobAnalyticsSummary


def _segment(total, paid, unpaid):
    if total <= 0:
        return {
            'total': 0,
            'paid': 0,
            'unpaid': 0,
            'paid_pct': 0,
            'unpaid_pct': 0,
            'paid_deg': 0,
            'unpaid_deg': 360,
            'empty': True,
        }
    paid_pct = round(100.0 * paid / total, 1)
    unpaid_pct = round(100.0 * unpaid / total, 1)
    paid_deg = round(360.0 * paid / total, 2)
    return {
        'total': total,
        'paid': paid,
        'unpaid': unpaid,
        'paid_pct': paid_pct,
        'unpaid_pct': unpaid_pct,
        'paid_deg': paid_deg,
        'unpaid_deg': 360 - paid_deg,
        'empty': False,
    }


@login_required
def analytics(request):
    summary = JobAnalyticsSummary.get_solo()
    context = {
        'summary': summary,
        'driving': _segment(summary.driving_total, summary.driving_paid, summary.driving_unpaid),
        'shuttle': _segment(summary.shuttle_total, summary.shuttle_paid, summary.shuttle_unpaid),
        'hotel': _segment(summary.hotel_total, summary.hotel_paid, summary.hotel_unpaid),
    }
    return render(request, 'analytics/analytics.html', context)
