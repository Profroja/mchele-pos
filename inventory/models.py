from django.db import models
import random

from auth.models import BaseModel


def generate_ean13():
    """Generate a random EAN-13 barcode with valid checksum."""
    while True:
        first_12 = ''.join([str(random.randint(0, 9)) for _ in range(12)])
        odd_sum = sum(int(first_12[i]) for i in range(0, 12, 2))
        even_sum = sum(int(first_12[i]) for i in range(1, 12, 2))
        checksum = (10 - (odd_sum + even_sum * 3) % 10) % 10
        barcode = first_12 + str(checksum)
        if not Package.objects.filter(barcode_value=barcode).exists():
            return barcode


class Package(BaseModel):
    class Status(models.TextChoices):
        IN_STOCK = 'in_stock', 'In Stock'
        SOLD = 'sold', 'Sold'
        DAMAGED = 'damaged', 'Damaged'
        RETURNED = 'returned', 'Returned'

    barcode_value = models.CharField(max_length=50, unique=True, editable=False)
    product_name = models.CharField(max_length=100, blank=True, default='', help_text='Optional product name')
    weight = models.DecimalField(max_digits=10, decimal_places=2, help_text='Weight in kg')
    selling_price = models.DecimalField(max_digits=10, decimal_places=2, help_text='Selling price')
    batch_number = models.CharField(max_length=50, blank=True, default='')
    production_date = models.DateField(null=True, blank=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.IN_STOCK,
    )
    notes = models.TextField(blank=True, default='')
    store = models.ForeignKey(
        'store.Store',
        on_delete=models.PROTECT,
        null=True, blank=True,
        related_name='packages',
        help_text='Store where this package is located',
    )

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Package'
        verbose_name_plural = 'Packages'

    def __str__(self):
        return f"{self.barcode_value} ({self.weight}kg)"

    def save(self, *args, **kwargs):
        if not self.barcode_value:
            self.barcode_value = generate_ean13()
        super().save(*args, **kwargs)
