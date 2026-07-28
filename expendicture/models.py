from django.db import models

from auth.models import BaseModel
from store.models import Store


class Expenditure(BaseModel):
    amount = models.DecimalField(max_digits=12, decimal_places=2, help_text='Expenditure amount')
    purpose = models.CharField(max_length=255, help_text='Purpose of the expenditure')
    notes = models.TextField(blank=True, default='')
    store = models.ForeignKey(
        Store,
        on_delete=models.PROTECT,
        null=True, blank=True,
        related_name='expenditures',
        help_text='Store this expenditure is associated with',
    )

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Expenditure'
        verbose_name_plural = 'Expenditures'

    def __str__(self):
        return f"{self.amount:,.0f} - {self.purpose} ({self.created_at.strftime('%d %b %Y')})"
