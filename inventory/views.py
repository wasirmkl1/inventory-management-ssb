import csv
from datetime import datetime, timedelta
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count, DecimalField, F, Q, Sum
from django.db.models.functions import Coalesce
from django.forms import inlineformset_factory
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.html import format_html

from .forms import ProductForm, ProductVariantForm, StockMovementForm
from .models import Brand, Category, Company, Product, ProductVariant, StockMovement

VariantFormSet = inlineformset_factory(
    Product,
    ProductVariant,
    form=ProductVariantForm,
    extra=3,
    can_delete=True,
)


def _apply_common_filters(qs, request):
    """Apply company/category/brand/country/unit/search filters shared by list views."""
    company = request.GET.get("company")
    category = request.GET.get("category")
    brand = request.GET.get("brand")
    country = request.GET.get("country")
    unit = request.GET.get("unit")
    search = request.GET.get("q")
    low_stock = request.GET.get("low_stock")

    if company:
        qs = qs.filter(product__brand__company_id=company)
    if category:
        qs = qs.filter(product__category_id=category)
    if brand:
        qs = qs.filter(product__brand_id=brand)
    if country:
        qs = qs.filter(product__country_of_origin=country)
    if unit:
        qs = qs.filter(unit=unit)
    if search:
        qs = qs.filter(product__name__icontains=search)
    if low_stock:
        qs = qs.filter(quantity_in_stock__lte=F("reorder_level"))
    return qs


def _filter_context(request):
    return {
        "companies": Company.objects.all(),
        "categories": Category.objects.all(),
        "brands": Brand.objects.select_related("company").all(),
        "countries": Product.objects.order_by().values_list(
            "country_of_origin", flat=True
        ).distinct(),
        "units": ProductVariant.UNIT_CHOICES,
        "selected": {
            "company": request.GET.get("company", ""),
            "category": request.GET.get("category", ""),
            "brand": request.GET.get("brand", ""),
            "country": request.GET.get("country", ""),
            "unit": request.GET.get("unit", ""),
            "q": request.GET.get("q", ""),
            "low_stock": request.GET.get("low_stock", ""),
            "sort": request.GET.get("sort", ""),
        },
    }


#: Quick range filter options for the Expiry tab: key -> number of days from today.
EXPIRY_RANGE_DAYS = {
    "7": 7,
    "15": 15,
    "30": 30,
    "90": 90,    # ~3 months
    "180": 180,  # ~6 months
    "365": 365,  # ~1 year
}

SORT_MAP = {
    "name": "product__name",
    "-name": "-product__name",
    "stock": "quantity_in_stock",
    "-stock": "-quantity_in_stock",
    "price": "selling_price",
    "-price": "-selling_price",
    "expiry": "expiry_date",
    "-expiry": "-expiry_date",
    "added": "product__date_added",
    "-added": "-product__date_added",
}


def inventory_list(request):
    """Main tab: all variants, with filters and sort."""
    qs = ProductVariant.objects.select_related(
        "product", "product__brand", "product__brand__company", "product__category"
    )
    qs = _apply_common_filters(qs, request)

    sort = request.GET.get("sort", "name")
    order = SORT_MAP.get(sort, "product__name")
    qs = qs.order_by(order)

    context = _filter_context(request)
    context["variants"] = qs
    context["active_tab"] = "inventory"
    return render(request, "inventory/inventory_list.html", context)


def expiry_list(request):
    """Expiry tab: variants that have an expiry date, nearest expiry first.

    Supports a quick range filter: expired / 7 / 30 / 90 / all.
    """
    qs = ProductVariant.objects.select_related(
        "product", "product__brand", "product__brand__company", "product__category"
    )
    qs = qs.filter(expiry_date__isnull=False)
    qs = _apply_common_filters(qs, request)

    today = timezone.localdate()
    range_filter = request.GET.get("range", "")
    if range_filter == "expired":
        qs = qs.filter(expiry_date__lt=today)
    elif range_filter in EXPIRY_RANGE_DAYS:
        days = EXPIRY_RANGE_DAYS[range_filter]
        qs = qs.filter(expiry_date__gte=today, expiry_date__lte=today + timedelta(days=days))

    sort = request.GET.get("sort", "expiry")
    order = SORT_MAP.get(sort, "expiry_date")
    qs = qs.order_by(order)

    context = _filter_context(request)
    context["variants"] = qs
    context["active_tab"] = "expiry"
    context["range_filter"] = range_filter
    return render(request, "inventory/expiry_list.html", context)


def _size_totals(variants):
    """Group variants by size_label (e.g. '400ml') and sum their stock.

    A product can have multiple rows for the same size if stock arrived in
    separate batches with different expiry dates -- this collapses those
    back into one total per size, so it's easy to see "how many 400ml do I
    have in total" without adding up each batch row by hand.
    """
    totals = {}
    order = []
    for v in variants:
        key = (v.size_label, v.unit)
        if key not in totals:
            totals[key] = {
                "size_label": v.size_label,
                "unit": v.get_unit_display(),
                "total_quantity": Decimal("0"),
                "is_discrete": v.unit in ProductVariant.DISCRETE_UNITS,
                "batch_count": 0,
            }
            order.append(key)
        totals[key]["total_quantity"] += v.quantity_in_stock
        totals[key]["batch_count"] += 1

    results = []
    for key in order:
        row = totals[key]
        if row["is_discrete"]:
            row["formatted_total"] = str(int(row["total_quantity"]))
        else:
            text = f"{row['total_quantity']:.2f}".rstrip("0").rstrip(".")
            row["formatted_total"] = text if text else "0"
        results.append(row)
    return results


def product_detail(request, pk):
    product = get_object_or_404(Product, pk=pk)
    variants = product.variants.all()
    size_totals = _size_totals(variants)
    return render(
        request,
        "inventory/product_detail.html",
        {"product": product, "variants": variants, "size_totals": size_totals},
    )


def product_add(request):
    """Add a new product, with all its size/weight variants in one form."""
    if request.method == "POST":
        form = ProductForm(request.POST)
        formset = VariantFormSet(request.POST, instance=Product())
        if form.is_valid():
            product = form.save(commit=False)
            formset = VariantFormSet(request.POST, instance=product)
            if formset.is_valid():
                product.save()
                formset.instance = product
                formset.save()
                messages.success(request, f"Product '{product.name}' added successfully.")
                return redirect("inventory:product_detail", pk=product.pk)
    else:
        form = ProductForm()
        formset = VariantFormSet(instance=Product())

    return render(
        request,
        "inventory/product_form.html",
        {"form": form, "formset": formset, "is_edit": False},
    )


def product_edit(request, pk):
    product = get_object_or_404(Product, pk=pk)
    if request.method == "POST":
        form = ProductForm(request.POST, instance=product)
        formset = VariantFormSet(request.POST, instance=product)
        if form.is_valid() and formset.is_valid():
            form.save()
            formset.save()
            messages.success(request, f"Product '{product.name}' updated.")
            return redirect("inventory:product_detail", pk=product.pk)
    else:
        form = ProductForm(instance=product)
        formset = VariantFormSet(instance=product)

    return render(
        request,
        "inventory/product_form.html",
        {"form": form, "formset": formset, "is_edit": True, "product": product},
    )


def _parse_date(value):
    """Parse a 'YYYY-MM-DD' string (from an <input type="date">) into a date, or None."""
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return None


def reports_index(request):
    """Landing page linking to the individual reports."""
    return render(request, "inventory/reports_index.html", {"active_tab": "reports"})


def inventory_report(request):
    """Current stock snapshot: quantities and stock value (cost & selling), with the
    usual company/brand/category/etc. filters, plus an optional 'date added' range and
    CSV export.
    """
    qs = ProductVariant.objects.select_related(
        "product", "product__brand", "product__brand__company", "product__category"
    )
    qs = _apply_common_filters(qs, request)

    date_from = _parse_date(request.GET.get("date_from"))
    date_to = _parse_date(request.GET.get("date_to"))
    if date_from:
        qs = qs.filter(product__date_added__gte=date_from)
    if date_to:
        qs = qs.filter(product__date_added__lte=date_to)

    sort = request.GET.get("sort", "name")
    order = SORT_MAP.get(sort, "product__name")
    qs = qs.order_by(order)

    if request.GET.get("export") == "csv":
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="inventory_report.csv"'
        writer = csv.writer(response)
        writer.writerow(
            ["Product", "Size", "Company", "Brand", "Category", "Origin", "Date Added",
             "Stock Qty", "Unit", "Cost Price", "Selling Price", "Stock Value (Cost)",
             "Stock Value (Selling)", "Batch Number", "Expiry Date"]
        )
        for v in qs:
            writer.writerow(
                [v.product.name, v.size_label,
                 v.product.brand.company.name if v.product.brand.company_id else "",
                 v.product.brand.name, v.product.category.name, v.product.country_of_origin,
                 v.product.date_added, v.formatted_quantity, v.unit, v.cost_price,
                 v.selling_price, v.stock_value_cost, v.stock_value_selling,
                 v.batch_number, v.expiry_date or ""]
            )
        return response

    decimal_field = DecimalField(max_digits=14, decimal_places=2)
    totals = qs.aggregate(
        total_cost_value=Coalesce(Sum(F("quantity_in_stock") * F("cost_price")), 0, output_field=decimal_field),
        total_selling_value=Coalesce(Sum(F("quantity_in_stock") * F("selling_price")), 0, output_field=decimal_field),
        total_variants=Count("id"),
    )
    totals["total_potential_profit"] = totals["total_selling_value"] - totals["total_cost_value"]

    context = _filter_context(request)
    context["variants"] = qs
    context["active_tab"] = "reports"
    context["totals"] = totals
    context["date_from"] = request.GET.get("date_from", "")
    context["date_to"] = request.GET.get("date_to", "")
    context["extra_range_field"] = format_html(
        '<label class="date-range-field">From (date added)'
        '<input type="date" name="date_from" value="{}"></label>'
        '<label class="date-range-field">To (date added)'
        '<input type="date" name="date_to" value="{}"></label>',
        context["date_from"],
        context["date_to"],
    )
    return render(request, "inventory/inventory_report.html", context)


def stock_movement_report(request):
    """Stock In / Stock Out report over a date range, with CSV export."""
    qs = StockMovement.objects.select_related(
        "variant", "variant__product", "variant__product__brand",
        "variant__product__brand__company", "variant__product__category",
    )

    company = request.GET.get("company")
    category = request.GET.get("category")
    brand = request.GET.get("brand")
    country = request.GET.get("country")
    unit = request.GET.get("unit")
    movement_type = request.GET.get("movement_type")
    search = request.GET.get("q")

    if company:
        qs = qs.filter(variant__product__brand__company_id=company)
    if category:
        qs = qs.filter(variant__product__category_id=category)
    if brand:
        qs = qs.filter(variant__product__brand_id=brand)
    if country:
        qs = qs.filter(variant__product__country_of_origin=country)
    if unit:
        qs = qs.filter(variant__unit=unit)
    if movement_type in ("in", "out"):
        qs = qs.filter(movement_type=movement_type)
    if search:
        qs = qs.filter(variant__product__name__icontains=search)

    date_from = _parse_date(request.GET.get("date_from"))
    date_to = _parse_date(request.GET.get("date_to"))
    if date_from:
        qs = qs.filter(created_at__date__gte=date_from)
    if date_to:
        qs = qs.filter(created_at__date__lte=date_to)

    qs = qs.order_by("-created_at")

    if request.GET.get("export") == "csv":
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="stock_movement_report.csv"'
        writer = csv.writer(response)
        writer.writerow(
            ["Date/Time", "Product", "Size", "Company", "Brand", "Movement", "Quantity", "Note"]
        )
        for m in qs:
            writer.writerow(
                [timezone.localtime(m.created_at).strftime("%Y-%m-%d %H:%M"),
                 m.variant.product.name, m.variant.size_label,
                 m.variant.product.brand.company.name if m.variant.product.brand.company_id else "",
                 m.variant.product.brand.name, m.get_movement_type_display(),
                 m.quantity, m.note]
            )
        return response

    decimal_field = DecimalField(max_digits=14, decimal_places=2)
    totals = qs.aggregate(
        total_in=Coalesce(
            Sum("quantity", filter=Q(movement_type="in")), 0, output_field=decimal_field
        ),
        total_out=Coalesce(
            Sum("quantity", filter=Q(movement_type="out")), 0, output_field=decimal_field
        ),
    )
    totals["net_change"] = totals["total_in"] - totals["total_out"]

    context = {
        "companies": Company.objects.all(),
        "categories": Category.objects.all(),
        "brands": Brand.objects.select_related("company").all(),
        "countries": Product.objects.order_by().values_list(
            "country_of_origin", flat=True
        ).distinct(),
        "units": ProductVariant.UNIT_CHOICES,
        "movements": qs,
        "totals": totals,
        "active_tab": "reports",
        "selected": {
            "company": request.GET.get("company", ""),
            "category": request.GET.get("category", ""),
            "brand": request.GET.get("brand", ""),
            "country": request.GET.get("country", ""),
            "unit": request.GET.get("unit", ""),
            "movement_type": request.GET.get("movement_type", ""),
            "q": request.GET.get("q", ""),
        },
        "date_from": request.GET.get("date_from", ""),
        "date_to": request.GET.get("date_to", ""),
    }
    return render(request, "inventory/stock_movement_report.html", context)


def stock_action(request, pk):
    """Handle a stock IN or OUT action for a single variant."""
    variant = get_object_or_404(ProductVariant, pk=pk)
    if request.method == "POST":
        form = StockMovementForm(request.POST)
        if form.is_valid():
            movement = form.save(commit=False)
            movement.variant = variant
            if movement.movement_type == "in":
                variant.quantity_in_stock += movement.quantity
            else:
                if movement.quantity > variant.quantity_in_stock:
                    messages.error(request, "Not enough stock for this OUT movement.")
                    return redirect("inventory:product_detail", pk=variant.product_id)
                variant.quantity_in_stock -= movement.quantity
            variant.save()
            movement.save()
            messages.success(
                request,
                f"{movement.get_movement_type_display()} of {movement.quantity} recorded for {variant}.",
            )
    return redirect("inventory:product_detail", pk=variant.product_id)
