from django.urls import path
from home import views

urlpatterns = [
    path('', views.login_view, name='login'),
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('logout/', views.logout_view, name='logout'),
    path('staff/', views.staff_view, name='staff'),
    path('stores/', views.stores_view, name='stores'),
    path('create_store/', views.create_store_view, name='create_store'),
    path('get_store/<int:store_id>/', views.get_store_view, name='get_store'),
    path('delete_store/<int:store_id>/', views.delete_store_view, name='delete_store'),
    path('manager/sales/', views.manager_sales_view, name='manager_sales'),
    path('manager/stock/', views.manager_stock_view, name='manager_stock'),
    path('create_user/', views.create_user_view, name='create_user'),
    path('get_user/<int:user_id>/', views.get_user_view, name='get_user'),
    path('delete_user/<int:user_id>/', views.delete_user_view, name='delete_user'),
]
