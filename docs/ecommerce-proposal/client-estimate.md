# Website Development Proposal — Sani Swapno Bazar

**Prepared for:** Sani Swapno Bazar
**Prepared by:** WJR & Team
**Date:** August 25, 2026
**Validity:** This estimate is valid for 14 days from the date above.

---

## 1. Project Overview

A customer-facing online storefront for Sani Swapno Bazar's product catalog, connected directly to your existing inventory system so products, prices, and stock levels stay accurate automatically — no manual double-entry.

Customers will be able to browse products by category, add items to a cart, and check out using:
- **Cash on Delivery (default)** — no payment needed until the order arrives.
- **bKash or Nagad in advance** — customer can choose to pay the full order amount ahead of time.
- **Advance delivery charge for larger orders** — to reduce fake/abandoned COD orders, orders above a set value require a small non-refundable advance before dispatch.

Every order is manually reviewed and confirmed by you (checking your bKash/Nagad app for reported transactions) before being shipped — no automated payment processing risk to manage.

---

## 2. Two Build Options

| | **Tier A — Recommended** | **Tier B — Future Upgrade** |
|---|---|---|
| Payment | Cash on Delivery + manually-verified bKash/Nagad advance | Cash on Delivery + fully automatic online bKash/Nagad/card payments |
| Requires trade license? | No | Yes (needed to open a payment gateway merchant account) |
| Price | **৳30,000** | **৳60,000** (fresh build) |
| Timeline | 3–5 weeks | +2–3 weeks on top of Tier A |

**Recommendation:** Start with Tier A. It fits your current stage with manual payment handling, and is fully upgradable to Tier B later once you have the business paperwork required for a payment gateway account — see Section 5 for upgrade pricing if you start with Tier A now.

---

## 3. Tier A — Cash-on-Delivery Storefront — ৳30,000

### Included
- Public storefront: home page, category pages, and product detail pages, built from your existing product catalog and images.
- Shopping cart (add/update/remove items).
- Checkout with:
  - Cash on Delivery as the default option.
  - Option to pay in advance via bKash or Nagad (customer enters their Transaction ID; you verify it manually).
  - **Tiered advance delivery charge** for larger orders *(pending your confirmation — see Section 8)*:
    - Orders above ৳3,000 → ৳130 advance required
    - Orders above ৳5,000 → ৳200 advance required
- Order notification sent directly to your WhatsApp/Messenger with full order details.
- Admin dashboard (extension of your existing inventory system) to view, confirm, and manage orders.
- Mobile-responsive design, since most customers will order from their phones.
- Product image support.
- Basic on-page SEO (page titles, descriptions) so products are findable via search engines.
- Performance optimizations: compressed/optimized images and fast-loading pages on reliable, always-on hosting.

### Not included in Tier A (available as add-ons — Section 6)
- Automatic online payment processing (Tier B).
- Automated fraud-order detection (available as an add-on — Section 6).
- Product photography or ad copywriting.
- Paid advertising/marketing setup.
- Ongoing content updates after launch (new product uploads are already possible directly through the existing admin panel).

### Price: **৳30,000** (one-time)
### Timeline: **3–5 weeks**

---

## 4. Tier B — Full Online Payment Storefront — ৳60,000 (Fresh Build)

Adds real-time, automatic bKash/Nagad/card payments at checkout via a licensed payment gateway, removing the need for manual transaction verification on advance/full payments.

**Requirement before this tier is possible:** a registered trade license and business bank account, needed to open a merchant account with a payment gateway provider. If you don't have this yet, Tier A is the right starting point.

### Price: **৳60,000** (one-time, fresh build)
### Timeline: **3–5 weeks** (built standalone) or **+2–3 weeks** if upgrading from an existing Tier A site (see Section 5)

---

## 5. Upgrading Later From Tier A to Tier B

If you start with Tier A now and decide to add automatic online payments later, you will **not** be charged the full ৳60,000 again — the storefront, cart, product pages, and admin dashboard you already paid for stay exactly as they are. The upgrade fee only covers the new payment-gateway work.

### Upgrade price: **৳35,000**
### Timeline: **2–3 weeks**

**What the upgrade fee adds:**

| New capability | What it means for you |
|---|---|
| Live bKash / Nagad / card payment at checkout | Customers can pay instantly online during checkout, not just via manual transfer |
| Secure payment gateway integration | Connects your site to a licensed payment provider (e.g. SSLCommerz) that handles the actual money movement safely |
| Automatic payment confirmation | No more manually checking your bKash/Nagad app for every advance payment — the system confirms it instantly |
| Failed/declined payment handling | Customers see a clear message and can retry if a payment fails, instead of a broken checkout |
| Refund support | Refunds can be processed through the payment provider if ever needed |
| Payment reconciliation view | A clear dashboard view of which orders are actually paid vs. still pending, so nothing gets shipped unpaid by mistake |
| Merchant account setup guidance | Support getting your trade license and business documents into the payment gateway's merchant onboarding process |

**What stays exactly the same (already covered by your Tier A payment):** the storefront design, product browsing, cart, mobile responsiveness, WhatsApp order notifications, and your inventory-connected admin dashboard.

---

## 6. Domain, Hosting & Other Recurring Charges

These are paid directly by you to the service providers — they are separate from the one-time build price above, and are not marked up unless you'd like WJR & Team to manage renewals on your behalf.

| Item | Estimated Cost | Notes |
|---|---|---|
| Domain name (.com) | ৳1,000 – ৳1,500 / year | Registered in your name, renews yearly |
| Website hosting | ৳0 – ৳7,000 / year | Reliable, always-on hosting to keep the site fast and avoid slow loading; a free tier may be sufficient at launch |
| Database hosting | ৳0 / year | Free tier is sufficient at your current scale |
| Image hosting | ৳0 / year | Free tier is sufficient at your current scale |
| SSL certificate (secure https://) | ৳0 | Included free with hosting |
| Payment gateway fees (Tier B only) | No fixed fee — approx. **2.5% per transaction** | Only applies once Tier B is active; no cost while on Tier A |
| Fraud-order detection (optional, see Section 7) | ৳0 / month at your current order volume | Free tier covers up to 500 checks/month; a paid plan (~৳999/month) is only needed if order volume grows significantly |

**Estimated total recurring cost: ৳1,000 – ৳8,500 per year**, mostly just the domain renewal if free-tier hosting is used.

---

## 7. Optional Add-ons (quoted separately if wanted)

| Add-on | Estimated Price |
|---|---|
| **Fraud-order detection** — automatically checks a customer's phone number against Bangladeshi courier delivery history (cancellations, failed deliveries, non-receipt) across **Steadfast, Pathao, RedX, Paperfly, and Carrybee** before you process a Cash on Delivery order, so risky orders can be flagged for extra confirmation | **৳5,000 one-time** integration fee. The checking service itself is free at your order volume (see Section 6); no ongoing cost unless you scale well beyond current volume |
| Monthly maintenance & support retainer (updates, fixes, new feature requests) | ৳1,500 – ৳3,000 / month |
| Managing domain/hosting renewals on your behalf | Small service fee, agreed separately |
| Product photography cleanup / re-shoots | Quoted separately, not a development service |
| SEO improvements | Quoted separately if requested |

---

## 8. Information Needed From You Before Starting

1. **Confirm the advance delivery charge rule exactly:** Orders above ৳3,000 → ৳130 advance, orders above ৳5,000 → ৳200 advance, orders below ৳3,000 → no advance (pure Cash on Delivery). *(Please confirm this is correct, or let us know the correct amounts.)*
2. The bKash and/or Nagad number(s) customers should send advance payments to.
3. The WhatsApp/phone number order notifications should be sent to.
4. Product photos to use (or confirmation to proceed with what's already in the inventory system).
5. Preferred domain name, if not already purchased.
6. Whether you'd like the fraud-order detection add-on included from launch, or added later (covers delivery history across **Steadfast, Pathao, RedX, Paperfly, and Carrybee**).

---

## 9. Payment Terms

- **50% advance** to begin work, **50% on delivery/launch.**
- **2 rounds of revisions** included after the first working version is shared; additional revision rounds billed separately at a rate agreed in advance.
- Domain and hosting will be set up under your own accounts (recommended, so you retain full ownership and control), with our support to set these up together.

---

## 10. Disclaimer

This estimate is based on the current catalog and requirements as discussed. Significant scope changes (e.g. major new features, multi-language support, or a large increase in catalog size) may require a revised quote.

---

**WJR & Team**
