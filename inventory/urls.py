from django.urls import path
from inventory import views

urlpatterns = [
    path('inventory/', views.inventory_dashboard_view, name='inventory_dashboard'),
    path('inventory/list/', views.inventory_list_view, name='inventory_list'),
    path('inventory/search/', views.stock_search_view, name='stock_search'),
    path('create_package/', views.create_package_view, name='create_package'),
    path('get_package/<int:package_id>/', views.get_package_view, name='get_package'),
    path('delete_package/<int:package_id>/', views.delete_package_view, name='delete_package'),
]
