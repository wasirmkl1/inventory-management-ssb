from django import forms
from django.contrib import admin

from .fields import FlexibleExpiryDateField
from .models import Brand, Category, Company, Product, ProductVariant, StockMovement


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    search_fields = ["name"]


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    search_fields = ["name"]


@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = ["name", "company"]
    list_filter = ["company"]
    search_fields = ["name", "company__name"]


class ProductVariantAdminForm(forms.ModelForm):
    expiry_date = FlexibleExpiryDateField(
        required=False,
        label="Expiry date",
        help_text="Full date: 21/08/26. Or just month/year: 08/26 (treated as the last day of that month).",
    )

    class Meta:
        model = ProductVariant
        fields = "__all__"


class ProductVariantInline(admin.TabularInline):
    """Lets you add all sizes (e.g. 90ml, 400ml) right on the Product page."""

    model = ProductVariant
    form = ProductVariantAdminForm
    extra = 1
    fields = [
        "size_label",
        "unit",
        "sku",
        "quantity_in_stock",
        "reorder_level",
        "cost_price",
        "selling_price",
        "batch_number",
        "expiry_date",
    ]


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ["name", "company_name", "brand", "category", "country_of_origin", "date_added"]
    list_filter = ["brand__company", "brand", "category", "country_of_origin"]
    search_fields = ["name", "brand__name", "brand__company__name", "category__name"]
    date_hierarchy = "date_added"
    inlines = [ProductVariantInline]

    @admin.display(description="Company")
    def company_name(self, obj):
        return obj.brand.company.name if obj.brand.company_id else "—"


@admin.register(ProductVariant)
class ProductVariantAdmin(admin.ModelAdmin):
    form = ProductVariantAdminForm
    list_display = [
        "product",
        "size_label",
        "unit",
        "quantity_in_stock",
        "reorder_level",
        "selling_price",
        "batch_number",
        "expiry_date",
    ]
    list_filter = ["unit", "product__brand__company", "product__brand", "product__category"]
    search_fields = ["product__name", "sku", "batch_number"]
    date_hierarchy = "expiry_date"


@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    list_display = ["variant", "movement_type", "quantity", "created_at", "note"]
    list_filter = ["movement_type"]
    search_fields = ["variant__product__name"]
    date_hierarchy = "created_at"
