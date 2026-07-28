from django.urls import path
from expendicture import views

urlpatterns = [
    path('expenditures/', views.expenditure_list_view, name='expenditure_list'),
    path('create_expenditure/', views.create_expenditure_view, name='create_expenditure'),
    path('delete_expenditure/<int:expenditure_id>/', views.delete_expenditure_view, name='delete_expenditure'),
]
