from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models


class BaseModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='%(class)s_created',
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='%(class)s_updated',
    )

    class Meta:
        abstract = True


class User(AbstractUser, BaseModel):
    class Role(models.TextChoices):
        MANAGER = 'manager', 'Manager'
        SALES_PERSON = 'sales_person', 'Sales Person'
        STOCK_PERSON = 'stock_person', 'Stock Person'

    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.SALES_PERSON,
    )
    phone = models.CharField(max_length=20, blank=True)
    is_active = models.BooleanField(default=True)
    store = models.ForeignKey(
        'store.Store',
        on_delete=models.PROTECT,
        null=True, blank=True,
        related_name='staff',
        help_text='Store assignment (not required for managers)',
    )

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"

    @property
    def is_manager(self):
        return self.role == self.Role.MANAGER

    @property
    def is_sales_person(self):
        return self.role == self.Role.SALES_PERSON

    @property
    def is_stock_person(self):
        return self.role == self.Role.STOCK_PERSON
