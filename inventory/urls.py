from django.urls import path

from . import views

app_name = "inventory"

urlpatterns = [
    path("", views.inventory_list, name="inventory_list"),
    path("expiry/", views.expiry_list, name="expiry_list"),
    path("reports/", views.reports_index, name="reports_index"),
    path("reports/inventory/", views.inventory_report, name="inventory_report"),
    path("reports/stock-movements/", views.stock_movement_report, name="stock_movement_report"),
    path("product/add/", views.product_add, name="product_add"),
    path("product/<int:pk>/", views.product_detail, name="product_detail"),
    path("product/<int:pk>/edit/", views.product_edit, name="product_edit"),
    path("variant/<int:pk>/stock/", views.stock_action, name="stock_action"),
]
