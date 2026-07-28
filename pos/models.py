from django.db import models

from auth.models import BaseModel
from inventory.models import Package


class Sale(BaseModel):
    receipt_number = models.CharField(max_length=30, unique=True, editable=False)
    package = models.ForeignKey(
        Package,
        on_delete=models.PROTECT,
        related_name='sales',
        null=True, blank=True,
    )
    barcode_value = models.CharField(max_length=50, blank=True, default='', help_text='Barcode (legacy single-item)')
    product_name = models.CharField(max_length=100, blank=True, default='')
    weight = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text='Weight in kg (legacy)')
    selling_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text='Selling price (legacy)')
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0, help_text='Total sale amount')
    customer_name = models.CharField(max_length=100, blank=True, default='', help_text='Optional customer name')
    customer_phone = models.CharField(max_length=20, blank=True, default='', help_text='Optional customer phone')
    payment_method = models.CharField(
        max_length=20,
        choices=[('cash', 'Cash'), ('mobile', 'Mobile Money'), ('card', 'Card')],
        default='cash',
    )
    sale_date = models.DateTimeField(auto_now_add=True)
    store = models.ForeignKey(
        'store.Store',
        on_delete=models.PROTECT,
        null=True, blank=True,
        related_name='sales',
        help_text='Store where this sale was made',
    )

    class Meta:
        ordering = ['-sale_date']
        verbose_name = 'Sale'
        verbose_name_plural = 'Sales'

    def __str__(self):
        return f"{self.receipt_number} - TSh {self.total_amount:,.0f}"

    def save(self, *args, **kwargs):
        if not self.receipt_number:
            import datetime
            now = datetime.datetime.now()
            prefix = f"RCP-{now.strftime('%Y%m%d')}-"
            last = Sale.objects.filter(
                receipt_number__startswith=prefix
            ).order_by('-receipt_number').first()
            if last:
                seq = int(last.receipt_number.split('-')[-1]) + 1
            else:
                seq = 1
            self.receipt_number = f"{prefix}{seq:04d}"
        super().save(*args, **kwargs)


class SaleItem(BaseModel):
    sale = models.ForeignKey(Sale, on_delete=models.CASCADE, related_name='items')
    package = models.ForeignKey(Package, on_delete=models.PROTECT, related_name='sale_items')
    barcode_value = models.CharField(max_length=50)
    product_name = models.CharField(max_length=100, blank=True, default='')
    weight = models.DecimalField(max_digits=10, decimal_places=2)
    selling_price = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.barcode_value} - {self.product_name} ({self.weight}kg)"
