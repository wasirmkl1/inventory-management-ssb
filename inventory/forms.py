from django import forms

from .fields import FlexibleExpiryDateField
from .models import Brand, Category, Product, ProductVariant, StockMovement


class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ["name", "brand", "category", "country_of_origin", "date_added", "description"]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 3}),
            "date_added": forms.DateInput(attrs={"type": "date"}),
        }


class ProductVariantForm(forms.ModelForm):
    expiry_date = FlexibleExpiryDateField(
        required=False,
        label="Expiry date",
        help_text="Full date: 21/08/26. Or just month/year if that's all the packaging shows: 08/26 (treated as the last day of that month).",
    )

    class Meta:
        model = ProductVariant
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


class StockMovementForm(forms.ModelForm):
    class Meta:
        model = StockMovement
        fields = ["movement_type", "quantity", "note"]


class QuickCategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ["name"]


class QuickBrandForm(forms.ModelForm):
    class Meta:
        model = Brand
        fields = ["name"]
