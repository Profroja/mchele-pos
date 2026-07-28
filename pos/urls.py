from django.urls import path
from pos import views

urlpatterns = [
    path('pos/', views.pos_dashboard_view, name='pos_dashboard'),
    path('pos/sales/', views.sales_list_view, name='sales_list'),
    path('create_sale/', views.create_sale_view, name='create_sale'),
    path('get_sale/<int:sale_id>/', views.get_sale_view, name='get_sale'),
    path('pos/search_barcode/', views.search_barcode_view, name='search_barcode'),
    path('pos/stock/', views.stock_lookup_view, name='pos_stock_lookup'),
    path('pos/funga-hesabu/', views.funga_hesabu_view, name='funga_hesabu'),
]
