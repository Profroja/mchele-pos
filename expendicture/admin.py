from django.contrib import admin

from .models import Expenditure


@admin.register(Expenditure)
class ExpenditureAdmin(admin.ModelAdmin):
    list_display = ['amount', 'purpose', 'store', 'created_by', 'created_at']
    list_filter = ['store', 'created_at']
    search_fields = ['purpose', 'notes']
