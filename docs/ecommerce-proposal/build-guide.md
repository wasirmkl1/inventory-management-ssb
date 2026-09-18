# Build Guide — Sani Swapno Bazar E-Commerce

**For:** you (the developer), building this solo with AI assistance
**Stack:** Django REST Framework (backend API) + React/Vite (frontend SPA) + PostgreSQL (Supabase or Neon) + Cloudinary (images) + Fly.io or Railway (backend hosting) + Vercel, Netlify, or Cloudflare Pages (frontend hosting)

This guide has three parts:
- **Part 1 — Tier A**, full step-by-step build (COD + manually-verified bKash/Nagad).
- **Part 2 — Tier B**, upgrading Part 1 with an automated payment gateway.
- **Part 3 — Optional**, fraud-order detection add-on.

Follow Part 1 fully before starting Part 2. Part 3 can be added at any point after Part 1's checkout flow exists.

---

# PART 1 — TIER A: FULL BUILD INSTRUCTIONS

## 1.0 Before You Start

- Keep the existing `inventory-management-ssb` app private, exactly as-is, for your stock/expiry/batch tracking. The new storefront is a separate system that reads/writes its own `Order` data, connected to the same database.
- **Repo structure** (single monorepo, easiest to manage solo):

```
sani-swapno-bazar/
├── backend/                 # Django + DRF project (the API)
│   ├── config/              # settings, urls, wsgi/asgi
│   ├── inventory/           # Company, Brand, Category, Product, ProductVariant, StockMovement
│   ├── storefront/          # NEW app: Order, OrderItem, public API views
│   ├── manage.py
│   └── requirements.txt
├── frontend/                # React (Vite) single-page app
│   ├── src/
│   │   ├── api/             # fetch/axios wrapper functions
│   │   ├── components/      # ProductCard, CartItem, Navbar, etc.
│   │   ├── pages/           # Home, Category, ProductDetail, Cart, Checkout, Confirmation
│   │   ├── context/         # CartContext (cart state + localStorage)
│   │   └── App.jsx
│   ├── package.json
│   └── vite.config.js
└── README.md
```

- **One database, two Django apps** inside the same project: `inventory` (your existing models, kept private/admin-only) and `storefront` (new: `Order`, `OrderItem`). Product/stock data stays in sync automatically — no duplication, no sync jobs.

## 1.1 Backend: Django REST Framework Setup

### Step 1 — Install dependencies
```bash
cd backend
python -m venv venv
source venv/bin/activate   # venv\Scripts\activate.bat on Windows
pip install django djangorestframework django-cors-headers dj-database-url python-decouple django-cloudinary-storage cloudinary whitenoise gunicorn
pip freeze > requirements.txt
```

### Step 2 — `settings.py` additions
```python
INSTALLED_APPS = [
    # ...existing apps (admin, auth, contenttypes, sessions, messages, staticfiles)...
    "rest_framework",
    "corsheaders",
    "cloudinary_storage",
    "cloudinary",
    "inventory",
    "storefront",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",   # must be high up, before CommonMiddleware
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

CORS_ALLOWED_ORIGINS = [
    "https://your-frontend-domain.com",
    "http://localhost:5173",  # Vite dev server, local development only
]

REST_FRAMEWORK = {
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.AllowAny"],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 24,
}
```
`AllowAny` is the default because product browsing must be public — specific views are explicitly locked down in Step 8.

### Step 3 — Create the `storefront` app
```bash
python manage.py startapp storefront
```

### Step 4 — Add `image_url` to your existing `Product` model
```python
# inventory/models.py — add to the existing Product class
image_url = models.URLField(blank=True, help_text="Paste the product's Cloudinary image URL here.")
```
Then:
```bash
python manage.py makemigrations inventory
python manage.py migrate
```
**Why a URL field, not a file upload field:** most hosting free tiers have an ephemeral filesystem — anything uploaded through the app disappears on the next deploy/restart. Uploading directly to Cloudinary's web console and pasting the URL avoids that entirely, with zero extra backend code.

### Step 5 — `storefront/models.py`
```python
from decimal import Decimal
from django.db import models
from inventory.models import ProductVariant

class Order(models.Model):
    PAYMENT_METHOD_CHOICES = [
        ("cod", "Cash on Delivery"),
        ("bkash", "bKash"),
        ("nagad", "Nagad"),
    ]
    PAYMENT_STATUS_CHOICES = [
        ("unpaid", "Unpaid (COD)"),
        ("advance_pending", "Advance Reported - Awaiting Verification"),
        ("advance_confirmed", "Advance Verified"),
        ("full_pending", "Full Payment Reported - Awaiting Verification"),
        ("full_confirmed", "Full Payment Verified"),
    ]

    customer_name = models.CharField(max_length=150)
    phone = models.CharField(max_length=20)
    address = models.TextField()
    payment_method = models.CharField(max_length=10, choices=PAYMENT_METHOD_CHOICES, default="cod")
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default="unpaid")
    transaction_id = models.CharField(max_length=50, blank=True, help_text="Customer-reported bKash/Nagad TrxID")
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    delivery_charge = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    advance_required = models.BooleanField(default=False)
    advance_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    is_confirmed = models.BooleanField(default=False, help_text="Manually confirmed after checking bKash/Nagad statement")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Order #{self.pk} - {self.customer_name}"


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    variant = models.ForeignKey(ProductVariant, on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)

    @property
    def line_total(self):
        return self.quantity * self.unit_price
```
```bash
python manage.py makemigrations storefront
python manage.py migrate
```

### Step 6 — Delivery/advance charge logic (`storefront/services.py`)
```python
from decimal import Decimal

def calculate_delivery_terms(subtotal: Decimal) -> dict:
    """Confirm exact thresholds with the client before relying on this in production.
    Current assumption: >5000 -> 200tk advance, >3000 -> 130tk advance, else none."""
    if subtotal > Decimal("5000"):
        return {"advance_required": True, "advance_amount": Decimal("200")}
    if subtotal > Decimal("3000"):
        return {"advance_required": True, "advance_amount": Decimal("130")}
    return {"advance_required": False, "advance_amount": Decimal("0")}
```
**Always call this server-side** when an order is created — never trust an advance amount sent from the frontend.

### Step 7 — Serializers (`storefront/serializers.py`)
```python
from rest_framework import serializers
from inventory.models import Product, ProductVariant
from .models import Order

class ProductVariantPublicSerializer(serializers.ModelSerializer):
    """Public-safe fields only -- no cost_price, batch_number, or exact stock counts."""
    in_stock = serializers.SerializerMethodField()

    class Meta:
        model = ProductVariant
        fields = ["id", "size_label", "selling_price", "in_stock"]

    def get_in_stock(self, obj):
        return obj.quantity_in_stock > 0


class ProductPublicSerializer(serializers.ModelSerializer):
    variants = ProductVariantPublicSerializer(many=True, read_only=True)
    category = serializers.StringRelatedField()
    brand = serializers.StringRelatedField()

    class Meta:
        model = Product
        fields = ["id", "name", "description", "category", "brand", "image_url", "variants"]


class OrderItemInputSerializer(serializers.Serializer):
    variant_id = serializers.IntegerField()
    quantity = serializers.IntegerField(min_value=1)


class OrderCreateSerializer(serializers.Serializer):
    customer_name = serializers.CharField(max_length=150)
    phone = serializers.CharField(max_length=20)
    address = serializers.CharField()
    payment_method = serializers.ChoiceField(choices=Order.PAYMENT_METHOD_CHOICES)
    transaction_id = serializers.CharField(max_length=50, required=False, allow_blank=True)
    items = OrderItemInputSerializer(many=True)
```

### Step 8 — Views (`storefront/views.py`)
```python
from decimal import Decimal
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from inventory.models import Product, ProductVariant
from .models import Order, OrderItem
from .serializers import ProductPublicSerializer, OrderCreateSerializer
from .services import calculate_delivery_terms


class ProductListView(generics.ListAPIView):
    serializer_class = ProductPublicSerializer

    def get_queryset(self):
        qs = Product.objects.prefetch_related("variants").select_related("category", "brand")
        category = self.request.query_params.get("category")
        if category:
            qs = qs.filter(category__id=category)
        return qs


class ProductDetailView(generics.RetrieveAPIView):
    queryset = Product.objects.prefetch_related("variants").select_related("category", "brand")
    serializer_class = ProductPublicSerializer


class OrderCreateView(APIView):
    def post(self, request):
        serializer = OrderCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        subtotal = Decimal("0")
        line_items = []
        for item in data["items"]:
            variant = get_object_or_404(ProductVariant, pk=item["variant_id"])
            if item["quantity"] > variant.quantity_in_stock:
                return Response({"error": f"Not enough stock for {variant}"}, status=400)
            line_total = variant.selling_price * item["quantity"]
            subtotal += line_total
            line_items.append((variant, item["quantity"], variant.selling_price))

        terms = calculate_delivery_terms(subtotal)

        order = Order.objects.create(
            customer_name=data["customer_name"],
            phone=data["phone"],
            address=data["address"],
            payment_method=data["payment_method"],
            transaction_id=data.get("transaction_id", ""),
            subtotal=subtotal,
            advance_required=terms["advance_required"],
            advance_amount=terms["advance_amount"],
            payment_status="advance_pending" if data["payment_method"] != "cod" else "unpaid",
        )
        for variant, qty, price in line_items:
            OrderItem.objects.create(order=order, variant=variant, quantity=qty, unit_price=price)

        return Response({
            "order_id": order.pk,
            "subtotal": subtotal,
            "advance_required": terms["advance_required"],
            "advance_amount": terms["advance_amount"],
        }, status=status.HTTP_201_CREATED)
```

### Step 9 — URLs
```python
# storefront/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path("products/", views.ProductListView.as_view(), name="product-list"),
    path("products/<int:pk>/", views.ProductDetailView.as_view(), name="product-detail"),
    path("orders/", views.OrderCreateView.as_view(), name="order-create"),
]

# config/urls.py
from django.contrib import admin
from django.urls import include, path
urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("inventory.urls")),       # existing private inventory pages
    path("api/", include("storefront.urls")),  # new public API
]
```

### Step 10 — Admin: manual payment confirmation workflow
```python
# storefront/admin.py
from django.contrib import admin
from .models import Order, OrderItem

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ["id", "customer_name", "phone", "payment_method", "payment_status", "subtotal", "is_confirmed", "created_at"]
    list_filter = ["payment_method", "payment_status", "is_confirmed"]
    inlines = [OrderItemInline]
    actions = ["mark_confirmed"]

    def mark_confirmed(self, request, queryset):
        queryset.update(is_confirmed=True)
    mark_confirmed.short_description = "Mark selected orders as payment-confirmed"
```

### Step 11 — Lock down the existing private inventory views
Your existing `inventory/views.py` (`product_add`, `product_edit`, `stock_action`) currently has **no login check applied**, even though `login_required` is imported. Before going public, add the decorator to each:
```python
from django.contrib.auth.decorators import login_required

@login_required
def product_add(request):
    ...

@login_required
def product_edit(request, pk):
    ...

@login_required
def stock_action(request, pk):
    ...
```
This is a required step, not optional — skipping it means anyone who finds the URL could edit your live inventory once the site is public.

## 1.2 Images (Cloudinary)

1. Sign up for Cloudinary's free tier.
2. Upload each product photo through Cloudinary's web console.
3. Copy the resulting image URL into the `image_url` field on that `Product` (via Django Admin).
4. Append `f_auto,q_auto` as a URL transformation parameter for automatic compression/format conversion — no extra code needed.

## 1.3 Frontend: React (Vite) Setup

### Step 1 — Scaffold
```bash
npm create vite@latest frontend -- --template react
cd frontend
npm install axios react-router-dom @tanstack/react-query
```
`@tanstack/react-query` caches API responses so navigating between pages feels instant instead of refetching every time.

### Step 2 — Pages to build
- `Home.jsx` — featured categories/products
- `CategoryPage.jsx` — paginated product grid, filterable
- `ProductDetailPage.jsx` — variant/size selector, add to cart
- `CartPage.jsx` — review/update quantities
- `CheckoutPage.jsx` — customer info form + payment method + dynamic advance-charge display
- `OrderConfirmationPage.jsx` — order summary + WhatsApp link button

### Step 3 — Cart context (client-side, `localStorage`-backed)
```jsx
// src/context/CartContext.jsx
import { createContext, useContext, useEffect, useState } from "react";

const CartContext = createContext();

export function CartProvider({ children }) {
  const [items, setItems] = useState(() => JSON.parse(localStorage.getItem("cart") || "[]"));

  useEffect(() => {
    localStorage.setItem("cart", JSON.stringify(items));
  }, [items]);

  const addItem = (variantId, name, price, quantity = 1) => {
    setItems((prev) => {
      const existing = prev.find((i) => i.variantId === variantId);
      if (existing) {
        return prev.map((i) => i.variantId === variantId ? { ...i, quantity: i.quantity + quantity } : i);
      }
      return [...prev, { variantId, name, price, quantity }];
    });
  };

  const subtotal = items.reduce((sum, i) => sum + i.price * i.quantity, 0);

  return (
    <CartContext.Provider value={{ items, addItem, subtotal, setItems }}>
      {children}
    </CartContext.Provider>
  );
}

export const useCart = () => useContext(CartContext);
```

### Step 4 — Checkout UI mirrors delivery-charge logic (for instant feedback only)
```jsx
function calculateDeliveryTerms(subtotal) {
  if (subtotal > 5000) return { advanceRequired: true, advanceAmount: 200 };
  if (subtotal > 3000) return { advanceRequired: true, advanceAmount: 130 };
  return { advanceRequired: false, advanceAmount: 0 };
}
```
The **backend recalculates this independently** on submission (Step 6 above) — a tampered frontend value can never change what's actually charged/confirmed.

### Step 5 — Submit order
```jsx
const res = await axios.post(`${import.meta.env.VITE_API_BASE_URL}/api/orders/`, {
  customer_name, phone, address, payment_method, transaction_id,
  items: cartItems.map(i => ({ variant_id: i.variantId, quantity: i.quantity })),
});
// Use res.data (server-confirmed subtotal/advance_amount) for the confirmation page and WhatsApp message.
```

### Step 6 — WhatsApp deep link
```jsx
function buildWhatsAppLink(order, items) {
  const lines = [
    `New order from ${order.customer_name} (${order.phone})`,
    ...items.map(i => `- ${i.name} x${i.quantity}`),
    `Subtotal: ${order.subtotal} BDT`,
    order.advance_required ? `Advance required: ${order.advance_amount} BDT` : "COD - no advance",
    `Address: ${order.address}`,
  ];
  const text = encodeURIComponent(lines.join("\n"));
  return `https://wa.me/8801XXXXXXXXX?text=${text}`;
}
```

### Step 7 — Environment variables
```
# frontend/.env
VITE_API_BASE_URL=https://api.saniswapnobazar.com
```

## 1.4 Security Checklist (Tier A)
- [ ] Public API exposes only public-safe fields — never `cost_price`, `batch_number`, or exact stock counts.
- [ ] `OrderCreateView` recalculates subtotal/advance charge server-side — never trusts a frontend-sent total.
- [ ] `CORS_ALLOWED_ORIGINS` set to your actual frontend domain only — never `"*"` in production.
- [ ] `@login_required` added to `product_add`, `product_edit`, `stock_action` (Step 11 above).
- [ ] `DEBUG = False` in production, with `ALLOWED_HOSTS`/`CSRF_TRUSTED_ORIGINS` set correctly for both domains.
- [ ] HTTPS enforced on both frontend and backend.
- [ ] Basic input validation on order creation (required fields, phone format) to reduce spam/fake orders.

## 1.5 Performance Checklist (Tier A)
- [ ] Frontend deployed as a static build to Vercel/Netlify/Cloudflare Pages — CDN-served, no cold start.
- [ ] Backend deployed on Fly.io or Railway (not a free tier that sleeps); pick a region close to Bangladesh if available.
- [ ] Cloudinary URLs include `f_auto,q_auto`.
- [ ] `loading="lazy"` on all product images below the fold.
- [ ] API responses paginated (`PAGE_SIZE = 24`).
- [ ] React Query caching enabled.
- [ ] `select_related`/`prefetch_related` on every queryset touching related models.

## 1.6 Testing Checklist (Tier A)
- [ ] Place a test order for each payment method: COD, bKash advance, Nagad advance, full advance.
- [ ] Test order **below ৳3,000** → confirm no advance requested.
- [ ] Test order **between ৳3,000–5,000** → confirm ৳130 advance requested.
- [ ] Test order **above ৳5,000** → confirm ৳200 advance requested.
- [ ] Confirm test orders appear correctly in Django Admin, and "mark confirmed" works.
- [ ] Test on an actual phone over mobile data, not just wifi/laptop.
- [ ] Confirm stock doesn't oversell (order more than available quantity — should be rejected).
- [ ] Confirm the WhatsApp link opens correctly with the pre-filled message on Android and iOS.

## 1.7 Deployment Steps (Tier A)
1. **Database:** create a Postgres project on Supabase or Neon, copy the connection string.
2. **Backend:** connect `backend/` to Fly.io or Railway, set environment variables (`SECRET_KEY`, `DEBUG=False`, `ALLOWED_HOSTS`, `DATABASE_URL`, `CORS_ALLOWED_ORIGINS`, Cloudinary keys), deploy, run migrations, create a superuser.
3. **Frontend:** connect `frontend/` to Vercel/Netlify/Cloudflare Pages, set `VITE_API_BASE_URL` to the deployed backend URL, deploy.
4. **Domain:** point the root domain to the frontend host, a subdomain (e.g. `api.saniswapnobazar.com`) to the backend host. Update `ALLOWED_HOSTS`/`CORS_ALLOWED_ORIGINS` to match.
5. **SSL:** automatic via both hosts — verify the padlock shows on both domains after DNS propagates.

## 1.8 Suggested Timeline (Tier A)

| Week | Focus |
|---|---|
| 1 | Backend: models, API endpoints, admin, delivery-charge logic |
| 2 | Frontend: product pages, cart |
| 3 | Checkout flow, COD/bKash/Nagad/advance logic, WhatsApp notification |
| 4 | Responsive styling pass, image optimization, full testing |
| 5 (buffer) | Deployment, domain setup, bug fixes |

---

# PART 2 — TIER B: UPGRADING TO AN AUTOMATED PAYMENT GATEWAY

Only start this part once Part 1 is live and stable. This adds SSLCommerz (or a similar licensed BD payment gateway) so bKash/Nagad/card payments are processed automatically instead of manually verified.

## 2.0 Prerequisite
The client must have a **registered trade license and business bank account** to open a merchant account with the payment gateway. Confirm this before starting — do not begin integration work without confirmed merchant credentials, since sandbox testing can proceed without them but production cannot go live without them.

## 2.1 Install the gateway SDK
```bash
pip install sslcommerz-python   # or the current officially maintained package -- verify latest on PyPI before installing
```

## 2.2 New model fields on `Order`
```python
# storefront/models.py -- add to Order
gateway_transaction_id = models.CharField(max_length=100, blank=True)
gateway_val_id = models.CharField(max_length=100, blank=True)
gateway_status = models.CharField(max_length=30, blank=True)
```
```bash
python manage.py makemigrations storefront
python manage.py migrate
```

## 2.3 Initiate-payment endpoint
```python
# storefront/gateway_views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from django.conf import settings
from .models import Order
import requests

class InitiatePaymentView(APIView):
    def post(self, request, order_id):
        order = Order.objects.get(pk=order_id)
        payload = {
            "store_id": settings.SSLCOMMERZ_STORE_ID,
            "store_passwd": settings.SSLCOMMERZ_STORE_PASSWORD,
            "total_amount": str(order.subtotal),
            "currency": "BDT",
            "tran_id": f"order-{order.pk}",
            "success_url": f"{settings.BACKEND_BASE_URL}/api/payments/success/",
            "fail_url": f"{settings.BACKEND_BASE_URL}/api/payments/fail/",
            "cancel_url": f"{settings.BACKEND_BASE_URL}/api/payments/cancel/",
            "cus_name": order.customer_name,
            "cus_phone": order.phone,
            "cus_add1": order.address,
        }
        resp = requests.post(settings.SSLCOMMERZ_API_URL, data=payload, timeout=10)
        data = resp.json()
        return Response({"payment_url": data.get("GatewayPageURL")})
```
**Verify the exact request/response field names against SSLCommerz's current official API documentation before implementing** — payment gateway APIs change field names between versions, and this is the single most important step to get right, since it directly handles money.

## 2.4 Webhook/callback handling — verify, don't trust blindly
```python
class PaymentSuccessCallbackView(APIView):
    def post(self, request):
        val_id = request.data.get("val_id")
        tran_id = request.data.get("tran_id")

        # CRITICAL: always call SSLCommerz's "Order Validation API" server-to-server
        # to confirm val_id is genuine before marking anything as paid.
        # Never trust the success callback alone -- it can be spoofed.
        is_valid = verify_with_gateway(val_id)  # implement using their validation endpoint

        if is_valid:
            order_pk = tran_id.replace("order-", "")
            order = Order.objects.get(pk=order_pk)
            order.gateway_val_id = val_id
            order.gateway_status = "validated"
            order.payment_status = "full_confirmed"
            order.is_confirmed = True
            order.save()
        return Response({"status": "ok"})
```
This server-to-server validation step is the most important security control in Tier B — skipping it means anyone could fake a "payment successful" callback.

## 2.5 Frontend changes
- Checkout page adds a "Pay Now" button when bKash/Nagad/Card is selected, calling `InitiatePaymentView` and redirecting the browser to the returned `payment_url`.
- `OrderConfirmationPage.jsx` handles both the redirect-back-successful case and a "payment failed, retry" case.

## 2.6 Testing Checklist (Tier B)
- [ ] Full sandbox test cycle: successful payment, failed payment, cancelled payment, before touching production credentials.
- [ ] Confirm server-to-server validation actually rejects a forged/tampered callback (test this deliberately).
- [ ] Confirm order stock/status updates only happen after validation succeeds, never on the raw callback alone.
- [ ] Test refund flow through the gateway's dashboard/API.
- [ ] Load-test nothing critical — but do manually test what happens if a customer closes the browser mid-payment (order should stay in a pending state, not silently lost).

## 2.7 Suggested Timeline (Tier B upgrade)
| Week | Focus |
|---|---|
| 1 | Merchant account/API credentials, sandbox integration, initiate-payment endpoint |
| 2 | Callback/webhook handling + server-to-server validation, frontend payment UI |
| 3 (buffer) | Full sandbox testing, production cutover, live monitoring after launch |

---

# PART 3 — OPTIONAL: FRAUD-ORDER DETECTION

Checks a customer's phone number against Bangladeshi courier delivery history (successful deliveries vs. cancellations/non-receipt) before a Cash on Delivery order is processed, using a BD-specific fraud-checking API.

## 3.1 Choosing a provider

Several small, independent Bangladeshi providers offer this kind of check. None of them are large, established platforms with a long public track record (unlike, say, a payment gateway) — they're niche developer tools, so this decision should be revisited periodically rather than treated as permanent.

| Provider | Couriers covered | Pricing | Fit for this stack |
|---|---|---|---|
| **FraudDetect** ([courierapi.chowdhury.bd](https://courierapi.chowdhury.bd/)) | Steadfast, Pathao, RedX, Paperfly, Carrybee (5) | Free: 500 checks/mo · Pro: ৳999/mo for 10,000 checks | **Recommended — used below.** Plain REST API (`POST /api/v1/check`, JSON in/out), framework-agnostic, integrates cleanly with Django via `requests`. No WordPress/WooCommerce dependency, and pricing is transparent and verifiable. |
| FraudChecker BD ([fraudchecker.link](https://fraudchecker.link/)) | Steadfast, Pathao, RedX, Paperfly (4) | ৳100–400/mo depending on daily search volume; developer API key included | Cheaper per-check, but the public site is entirely WordPress/WooCommerce-plugin-oriented with no visible developer API docs — a real integration-risk unknown for a custom Django/React build. Worth re-checking if their API documentation improves. |
| BD Courier "Fraud Block" plugin ([plugins.bdcourier.com](https://plugins.bdcourier.com/)) | N/A | ৳499 one-time | Not actually comparable — this blocks IPs/duplicate orders locally inside WooCommerce, it doesn't check courier delivery history at all. Not applicable to this stack. |
| FraudPeek ([fraudpeek.com](https://fraudpeek.com/)) | 3+ couriers | 50 free lookups/day; a "Developer API" is mentioned but has no public pricing page | Pricing opacity beyond the free tier makes it unsuitable to commit to for a costed estimate. |

**Recommendation: use FraudDetect (courierapi.chowdhury.bd).** It covers the most couriers (5, including Carrybee which the others miss), has the only genuinely documented, stack-agnostic REST API of the options above, and transparent pricing you can actually stand behind in a client estimate.

| Plan | Monthly checks | Price |
|---|---|---|
| Free | 500/month | ৳0 |
| Pro | 10,000/month | ৳999/month |
| Enterprise | Unlimited | Custom |

At current order volume, the Free tier is sufficient (roughly 150 checks/month at 4-5 orders/day). Re-evaluate only if order volume grows well beyond ~15/day sustained.

**Design for provider swap-ability:** since these are all small, unverified providers, keep the integration behind the single `check_fraud_risk()` function shown below rather than calling the provider's API directly from multiple places. If FraudDetect's reliability or pricing changes, or a stronger competitor emerges (e.g. better docs from FraudChecker BD), swapping providers becomes a one-function change instead of a rewrite.

## 3.2 Backend integration
```python
# storefront/fraud_check.py
import requests
from django.conf import settings

def check_fraud_risk(phone: str) -> dict:
    """Returns aggregate delivery/cancel ratio for a phone number, or None if the check fails.
    Never block an order on this failing -- treat it as informational only."""
    try:
        resp = requests.post(
            "https://courierapi.chowdhury.bd/api/v1/check",
            headers={"X-Api-Key": settings.FRAUD_CHECK_API_KEY},
            json={"phone": phone},
            timeout=5,
        )
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException:
        return None
```

## 3.3 Wire it into order creation (informational, non-blocking)
```python
# storefront/views.py -- inside OrderCreateView.post(), after saving the order
from .fraud_check import check_fraud_risk

fraud_data = check_fraud_risk(order.phone)
if fraud_data:
    order.fraud_success_ratio = fraud_data["aggregate"]["success_ratio"]
    order.fraud_cancel_ratio = fraud_data["aggregate"]["cancel_ratio"]
    order.save()
```
Add matching fields to the `Order` model (`fraud_success_ratio`, `fraud_cancel_ratio`, both nullable decimals), migrate, and surface them in `OrderAdmin.list_display` so you can see risk at a glance before confirming/shipping an order.

**Important design decision:** treat this as informational, never as an automatic blocker. A low success ratio should prompt you to call the customer to confirm before shipping, not silently cancel their order — false positives are common (e.g. a customer who moved cities, or shared a number with someone else), and auto-rejecting real customers costs you more than the fraud it prevents.

## 3.4 Testing
- [ ] Test with a known low-risk number (should show a normal/high success ratio).
- [ ] Test with the API key intentionally wrong/missing — confirm the order still saves successfully (non-blocking behavior working correctly).
- [ ] Confirm the risk data is visible in Django Admin next to each order.
