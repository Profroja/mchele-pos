from django.db import models
from auth.models import BaseModel


class Store(BaseModel):
    name = models.CharField(max_length=100, unique=True)
    location = models.CharField(max_length=200, blank=True, default='')
    phone = models.CharField(max_length=20, blank=True, default='')
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Store'
        verbose_name_plural = 'Stores'

    def __str__(self):
        return self.name
