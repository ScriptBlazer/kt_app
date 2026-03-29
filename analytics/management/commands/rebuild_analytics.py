from django.core.management.base import BaseCommand

from analytics.services import rebuild_analytics


class Command(BaseCommand):
    help = 'Recompute job analytics counters from driving, shuttle, and hotel tables.'

    def handle(self, *args, **options):
        summary = rebuild_analytics()
        self.stdout.write(
            self.style.SUCCESS(
                'Analytics rebuilt: '
                f'driving {summary.driving_total} '
                f'({summary.driving_paid} paid / {summary.driving_unpaid} unpaid), '
                f'shuttle {summary.shuttle_total}, '
                f'hotel {summary.hotel_total}.'
            )
        )
