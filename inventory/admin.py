from django.contrib import admin

from inventory.models import Package


@admin.register(Package)
class PackageAdmin(admin.ModelAdmin):
    list_display = ('barcode_value', 'product_name', 'weight', 'selling_price', 'status', 'batch_number', 'created_at')
    list_filter = ('status', 'weight')
    search_fields = ('barcode_value', 'batch_number')
    readonly_fields = ('barcode_value', 'created_at', 'updated_at')
