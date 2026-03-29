from django.db import models


class JobAnalyticsSummary(models.Model):
    """Singleton summary row (pk=1) maintained by signals and rebuild_analytics."""

    driving_total = models.PositiveIntegerField(default=0)
    driving_paid = models.PositiveIntegerField(default=0)
    driving_unpaid = models.PositiveIntegerField(default=0)

    shuttle_total = models.PositiveIntegerField(default=0)
    shuttle_paid = models.PositiveIntegerField(default=0)
    shuttle_unpaid = models.PositiveIntegerField(default=0)

    hotel_total = models.PositiveIntegerField(default=0)
    hotel_paid = models.PositiveIntegerField(default=0)
    hotel_unpaid = models.PositiveIntegerField(default=0)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Job analytics summary'
        verbose_name_plural = 'Job analytics summary'

    def __str__(self):
        return 'Job analytics summary'

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def get_solo(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj
