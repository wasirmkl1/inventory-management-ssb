---
inclusion: always
---

# Sani Shwapno Bazar — Inventory Management

This is a **Django** web app for tracking inventory for a single online shop
(Sani Shwapno Bazar) that imports products (mostly from Saudi Arabia) and
sells them across Bangladesh. It is intentionally simple: one owner/user,
no multi-tenant concerns, no e-commerce/checkout — just inventory tracking
(products, stock levels, stock in/out history, expiry dates).

Read this file first in any new session before making changes, so
conventions stay consistent regardless of which chat session or Kiro
account is being used.

## Tech stack

- **Backend**: Django 4.2, Python 3.9–3.12 (avoid 3.14 locally — see
  "Known gotchas" below)
- **Database**: SQLite locally (zero setup, default when no `DATABASE_URL`
  env var is set) / PostgreSQL when hosted (via `dj-database-url`, set
  `DATABASE_URL`)
- **Frontend**: plain server-rendered HTML/CSS via Django templates — no
  JS framework, no build step, no npm. One small vanilla `<script>` block
  in `product_form.html` handles the dynamic "+ Add another size" button.
- **Styling**: single `static/css/style.css` file, teal color palette
  (CSS vars `--teal-*`), Google Fonts "Inter" loaded in `base.html`.
- **Static files**: whitenoise (`whitenoise.middleware.WhiteNoiseMiddleware`)
- **Env vars**: `python-decouple` reads `.env` locally if present (see
  `.env.example` for the full list); nothing is required to run locally.
- **Deployment target**: free tier hosting (Render + Neon Postgres) — see
  README for the walkthrough. `Procfile` and `build.sh` are set up for this.

## Project structure

```
config/                  Django project (settings, urls, wsgi/asgi)
inventory/                The one app — all business logic lives here
  models.py               Category, Company, Brand, Product, ProductVariant, StockMovement
  fields.py               FlexibleExpiryDateField (custom form field)
  forms.py                ProductForm, ProductVariantForm, StockMovementForm
  views.py                inventory_list, expiry_list, product_detail, product_add/edit, stock_action
  admin.py                Django Admin config (primary bulk-data-entry UI)
  urls.py                 App-level URL routes
  migrations/
templates/inventory/      HTML templates (base.html + one per view + _filter_bar.html partial)
static/css/style.css      All styling
requirements.txt, build.sh, Procfile, .env.example   Deployment/env config
```

## Data model — how it fits together

```
Company (optional)
  └─ Brand              (Brand.company is nullable FK)
       └─ Product        (name, category, country_of_origin, date_added)
            └─ ProductVariant   (size_label, unit, quantity, prices, expiry_date, batch_number)
                 └─ StockMovement   (audit log of every stock in/out)
```

Key design decisions, and **why** — do not "simplify" these away without
re-reading the conversation history that led to them:

- **Company sits above Brand, not above Product.** You set Company once
  per Brand (e.g. Brand "Garnier" → Company "L'Oréal") in Django Admin.
  Every Product under that brand inherits it automatically via
  `product.brand.company`. There is intentionally no `company` field on
  `Product` itself.
- **Stock is tracked per `ProductVariant`, never on `Product`.** A single
  product (e.g. "Amino Silk" shampoo) can have multiple variants for
  different sizes (90ml, 400ml) AND multiple variants for the **same**
  size when stock arrives in batches with different expiry dates (e.g.
  three separate 400ml rows: 7pcs/Feb2029, 1pc/June2029, 1pc/May2029).
  Seeing the same product name repeated multiple times on the Inventory
  tab is expected and correct — it means multiple batches/sizes exist,
  not a bug or duplicate data.
- **`ProductVariant.unit` controls how stock is *counted*, independent of
  `size_label`.** `size_label` is just a display string (e.g. "700ml").
  A bottled/boxed item should almost always have `unit="pcs"` (you're
  counting bottles, not millilitres) — `kg`/`g`/`l`/`ml` are only for
  genuinely loose/bulk stock sold by weight/volume. Getting this wrong
  is the most common data-entry mistake (see git history — this exact
  bug was reported and fixed once already).
- **`ProductVariant.formatted_quantity`** (a model property, not a
  template filter) renders stock for display: whole numbers for
  `DISCRETE_UNITS = {"pcs", "box", "pack"}` (no ".00"), decimals
  preserved-but-trimmed for weight/volume units. Always use this property
  in templates for displaying stock — never render `quantity_in_stock`
  directly, it's a raw `Decimal`.
- **`FlexibleExpiryDateField`** (`inventory/fields.py`) is a custom form
  field (not a model field — `ProductVariant.expiry_date` is a plain
  `DateField`) used everywhere expiry is entered, in both the custom
  form and Django Admin. It accepts `DD/MM/YY`, `DD/MM/YYYY`, `MM/YY`,
  `MM/YYYY` (any of `/`, `-`, `.` as separators), and legacy
  `YYYY-MM-DD`/`YYYY-MM`. **Month-only input is deliberately treated as
  the last day of that month** — many packaged goods only print a
  month/year expiry, and assuming the last day is the safer choice for
  an expiry warning system. Do not change this without discussing it —
  it was a deliberate, tested decision.
- **`Product.date_added`** is an editable `DateField` (not `auto_now_add`)
  defaulting to today, because the shop owner enters historical notebook
  records — dates need to be backdated, not locked to "when I typed
  this in".
- **`StockMovement`** is an append-only audit log. `stock_action` view
  updates `ProductVariant.quantity_in_stock` directly AND creates a
  `StockMovement` row — never bypass one or the other. Stock Out is
  rejected (with a user-facing error message, no exception) if the
  requested quantity exceeds current stock.

## Conventions to follow

- **One Django app** (`inventory`). Don't split into multiple apps unless
  the user explicitly asks — this project is intentionally small.
- **No JS framework, no build step.** Any new interactive behavior should
  be a small vanilla `<script>` block in the relevant template, consistent
  with the existing "+ Add another size" pattern in `product_form.html`.
- **Filter bar is shared** via `templates/inventory/_filter_bar.html`,
  included by both `inventory_list.html` and `expiry_list.html`. Add new
  filters there once, not duplicated in both templates.
- **`SORT_MAP` and `EXPIRY_RANGE_DAYS`** in `views.py` are the single
  source of truth for sort options and expiry quick-ranges — extend those
  dicts rather than adding ad-hoc branching.
- **Tables use `.table-wrapper` + `.action-col`** (see `style.css`) for
  horizontal scroll on narrow screens with a sticky right-hand action
  column (the "Manage" button). Any new list-style table should follow
  this same pattern for mobile usability.
- **Teal palette + Inter font** — defined via CSS custom properties at
  the top of `style.css` (`--teal-50` through `--teal-800`). Reuse these
  vars; don't introduce new ad-hoc colors.

## Known gotchas (learned the hard way — see git history)

- **Python 3.14 breaks Django 4.2's admin templates** with
  `AttributeError: 'super' object has no attribute 'dicts'`. This is a
  known Django/Python incompatibility (Django 4.2 only supports up to
  Python 3.13; Django 5.2+ is needed for 3.14 support). If a user reports
  this exact error, the fix is to use Python 3.10–3.13 for the venv, not
  to change the Django code. Do not attempt to "fix" this in application
  code.
- **Django inline formset field name prefix is `variants-`**, not the
  Django-default `productvariant_set-`, because `ProductVariant.product`
  uses `related_name="variants"`. Relevant when writing tests or manually
  constructing form data against the admin's `ProductVariantInline`.
- **`ProductVariant` default ordering is `["product__name", "size_label"]`**
  (alphabetical on size_label as a string) — "1L" sorts before "400ml"
  sorts before "90ml". Don't assume insertion order when writing tests or
  reasoning about which row appears first in the UI.
- Local `db.sqlite3` and `venv/` are gitignored — never commit them. Any
  verification/manual testing should create its own temp data and clean
  it up afterward (delete test Products/Brands/Companies/Categories
  before finishing), and never leave one-off test scripts in the repo
  root — delete them before committing.

## Workflow

- The user works from **Windows, cmd, inside VS Code**. Command examples
  in the README should be cmd-compatible (`venv\Scripts\activate.bat`,
  `rmdir /s /q`, etc.), not bash/PowerShell, unless asked otherwise.
- Every feature/fix should go through: implement → run migrations if the
  model changed → verify with real requests (not just "no errors") →
  clean up test data/scripts → commit on a new branch → push → open a PR
  via `gh api` → merge (this repo has one owner reviewing async, so
  merging agent-created PRs directly is the established pattern here —
  confirm with the user if that ever seems to change).
- Always leave the working tree clean before finishing: no stray test
  scripts, no local `db.sqlite3`, `git status` clean.
