"""Business OS online store: products, cart pricing, orders and the shop
pages (/<site>/shop/…), rendered inside the template's starter page like
custom pages. Prices always come from the database, never the browser."""
import html as html_lib
import json
import uuid
from decimal import Decimal, InvalidOperation

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import transaction
from django.utils import timezone

from ..models import Order, Product
from . import notify

RESERVED_PRODUCT_SLUGS = {"cart", "checkout", "data", "thanks"}
MAX_QTY = 20


class StoreError(Exception):
    pass


def available(site):
    return site.business_os_available


def price_cart(site, raw_items):
    """[{id, qty}] from the browser → (lines, total) at today's prices."""
    if not isinstance(raw_items, list) or not raw_items:
        raise StoreError("Your cart is empty.")
    qty_by_id = {}
    for item in raw_items[:50]:
        try:
            pid, qty = int(item.get("id")), int(item.get("qty"))
        except (TypeError, ValueError, AttributeError):
            continue
        if 1 <= qty <= MAX_QTY:
            qty_by_id[pid] = min(qty_by_id.get(pid, 0) + qty, MAX_QTY)
    products = {p.id: p for p in site.products.filter(id__in=qty_by_id, active=True)}
    lines, total = [], Decimal("0.00")
    for pid, qty in qty_by_id.items():
        product = products.get(pid)
        if product is None:
            continue
        if product.stock is not None and product.stock < qty:
            raise StoreError(f"Only {product.stock} of “{product.name}” left.")
        lines.append({"product_id": pid, "name": product.name, "price": str(product.price), "qty": qty})
        total += product.price * qty
    if not lines:
        raise StoreError("Your cart is empty.")
    return lines, total


def create_order(site, body):
    name = " ".join(str(body.get("name", "")).split())[:120]
    email = str(body.get("email", "")).strip()[:254]
    if not name:
        raise StoreError("Enter your name.")
    try:
        validate_email(email)
    except ValidationError:
        raise StoreError("Enter a valid email address.")
    lines, total = price_cart(site, body.get("items"))
    if total < Decimal("5.00"):
        raise StoreError("The minimum order is R5.")
    share = (total * settings.STORE_OWNER_SHARE_PERCENT / 100).quantize(Decimal("0.01"))
    return Order.objects.create(
        site=site,
        reference=f"{site.slug[:40]}-{uuid.uuid4().hex[:10]}",
        name=name,
        email=email,
        phone=" ".join(str(body.get("phone", "")).split())[:30],
        address=str(body.get("address", "")).strip()[:1000],
        items=lines,
        total=total,
        owner_share=share if site.store_payfast_merchant_id and site.store_payouts_approved else Decimal("0.00"),
    )


def mark_paid(order, amount_gross, payfast_payment_id):
    """ITN COMPLETE for an order. Returns False if the amount doesn't match."""
    try:
        received = Decimal(amount_gross)
    except (InvalidOperation, TypeError):
        return False
    if received != order.total:
        return False
    if order.status != Order.STATUS_PENDING:
        return True
    with transaction.atomic():
        order.status = Order.STATUS_PAID
        order.paid_at = timezone.now()
        order.payfast_payment_id = payfast_payment_id[:40]
        order.save(update_fields=["status", "paid_at", "payfast_payment_id"])
        for line in order.items:
            product = Product.objects.select_for_update().filter(id=line["product_id"]).first()
            if product and product.stock is not None:
                product.stock = max(product.stock - int(line["qty"]), 0)
                product.save(update_fields=["stock"])
    _email_order(order)
    return True


def _lines_text(order):
    return "\n".join(f"  {l['qty']} × {l['name']} @ R{l['price']}" for l in order.items)


def _email_order(order):
    site = order.site
    owner = site.email or (site.owner.email if site.owner_id else "")
    notify.send_email(
        owner,
        f"[{site.name}] New order {order.reference} — R{order.total}",
        f"New paid order on {site.name}.\n\n{_lines_text(order)}\nTotal: R{order.total}\n\n"
        f"Customer: {order.name} <{order.email}> {order.phone}\nDeliver to: {order.address or 'collection'}\n\n"
        "Manage it in your Vicinic portal: https://console.vicinic.co.za/#customers",
        reply_to=order.email,
    )
    notify.send_email(
        order.email,
        f"Your order from {site.name} ({order.reference})",
        f"Hi {order.name.split(' ')[0]},\n\nThanks for your order from {site.name}! Payment received.\n\n"
        f"{_lines_text(order)}\nTotal: R{order.total}\n\nWe'll be in touch about delivery. Reply to this email with any questions.",
        reply_to=owner or None,
    )


# --- Shop pages ---

def _money(value):
    return f"R{Decimal(value):,.2f}".replace(",", " ")


def _esc(value):
    return html_lib.escape(str(value or ""))


def _title(heading, lead=""):
    lead_html = f'<p class="lead mb-0">{_esc(lead)}</p>' if lead else ""
    return f'<section class="py-5 bg-light vicinic-page-title"><div class="container"><h1 class="mb-0">{_esc(heading)}</h1>{lead_html}</div></section>'


def _cart_link(base):
    return f'<p class="mb-0"><a class="vicinic-cart-link" href="{base}shop/cart/">🛒 Cart (<span class="vicinic-cart-count">0</span>)</a></p>'


def list_html(site, base):
    products = site.products.filter(active=True)
    if not products:
        grid = '<p class="text-muted">No products yet — check back soon.</p>'
    else:
        grid = "".join(
            '<div class="col-md-4"><div class="card h-100">'
            + (f'<a href="{base}shop/{p.slug}/"><img src="{_esc(p.image_url)}" alt="{_esc(p.name)}" class="vicinic-product-img"></a>' if p.image_url else "")
            + f'<div class="card-body"><h3 class="h5 card-title"><a href="{base}shop/{p.slug}/">{_esc(p.name)}</a></h3>'
            f'<p class="fw-bold">{_money(p.price)}</p>'
            + (
                f'<button type="button" class="vicinic-add" data-id="{p.id}">Add to cart</button>'
                if p.in_stock
                else '<p class="text-muted mb-0">Sold out</p>'
            )
            + "</div></div></div>"
            for p in products
        )
    return (
        _title("Shop", f"Order from {site.name} online")
        + f'<section class="py-5"><div class="container">{_cart_link(base)}<div class="row g-4 mt-2">{grid}</div></div></section>'
    )


def product_html(site, product, base):
    description = "".join(f"<p>{_esc(p)}</p>" for p in product.description.split("\n\n") if p.strip())
    image = f'<div class="col-lg-6"><img src="{_esc(product.image_url)}" alt="{_esc(product.name)}" class="vicinic-product-img rounded-3"></div>' if product.image_url else ""
    buy = (
        f'<label>Quantity <input type="number" class="vicinic-qty" min="1" max="{MAX_QTY}" value="1"></label> '
        f'<button type="button" class="vicinic-add" data-id="{product.id}" data-qty-from=".vicinic-qty">Add to cart</button>'
        if product.in_stock
        else '<p class="text-muted">Sold out</p>'
    )
    return (
        _title(product.name)
        + f'<section class="py-5"><div class="container"><p><a href="{base}shop/">← Shop</a></p>'
        f'<div class="row g-5">{image}<div class="col-lg-6"><p class="display-6 fw-bold">{_money(product.price)}</p>{description}'
        f'<div class="my-3">{buy}</div>{_cart_link(base)}</div></div></div></section>'
    )


def cart_html(site, base):
    return (
        _title("Your cart")
        + '<section class="py-5"><div class="container"><div id="vicinic-cart" class="row g-5">'
        '<div class="col-lg-6"><div id="vicinic-cart-lines"><p class="text-muted">Loading…</p></div></div>'
        '<div class="col-lg-6"><form id="vicinic-checkout" class="vicinic-checkout">'
        '<h2 class="h5">Your details</h2>'
        '<input name="name" placeholder="Full name" required maxlength="120">'
        '<input name="email" type="email" placeholder="Email" required maxlength="254">'
        '<input name="phone" type="tel" placeholder="Phone" maxlength="30">'
        '<textarea name="address" rows="3" placeholder="Delivery address (leave empty to collect)" maxlength="1000"></textarea>'
        '<button type="submit">Pay securely with PayFast</button><p class="vicinic-checkout-note text-muted"></p>'
        f'</form></div></div><p class="mt-2"><a href="{base}shop/">← Keep shopping</a></p></div></section>'
    )


def thanks_html(site, order, base):
    if order is None:
        return _title("Thank you") + f'<section class="py-5"><div class="container"><p><a href="{base}shop/">Back to the shop</a></p></div></section>'
    paid = order.status != Order.STATUS_PENDING
    message = (
        "Payment received — we've emailed you a confirmation."
        if paid
        else "We're confirming your payment with PayFast. You'll get an email as soon as it's through."
    )
    return (
        _title("Thank you for your order!", f"Order {order.reference}")
        + f'<section class="py-5"><div class="container"><p>{_esc(message)}</p>'
        f'<p class="fw-bold">Total: {_money(order.total)}</p><p><a href="{base}shop/">Back to the shop</a></p>'
        '<script>try{localStorage.removeItem(' + json.dumps(f"vicinic_cart_{site.slug}") + ')}catch(e){}</script></div></section>'
    )


STORE_CSS = """
.vicinic-sections .vicinic-product-img{width:100%;aspect-ratio:1/1;object-fit:cover}
.vicinic-sections .vicinic-add,.vicinic-sections .vicinic-checkout button{border:0;border-radius:8px;padding:10px 18px;font-weight:600;cursor:pointer;background:var(--vicinic-primary,#111);color:#fff}
.vicinic-sections .vicinic-checkout{display:flex;flex-direction:column;gap:10px}
.vicinic-sections .vicinic-checkout input,.vicinic-sections .vicinic-checkout textarea,.vicinic-sections .vicinic-qty{border:1px solid color-mix(in srgb,currentColor 25%,transparent);border-radius:8px;padding:9px 11px;font:inherit;background:transparent;color:inherit}
.vicinic-sections .vicinic-qty{width:80px}
.vicinic-sections .vicinic-cart-row{display:flex;justify-content:space-between;align-items:center;gap:12px;padding:10px 0;border-bottom:1px solid color-mix(in srgb,currentColor 15%,transparent)}
.vicinic-sections .vicinic-cart-row button{background:none;border:0;color:inherit;cursor:pointer;font-size:18px}
"""


def store_script(site, base):
    """Cart kept in localStorage; checkout posts ids + quantities only."""
    key = json.dumps(f"vicinic_cart_{site.slug}")
    return f"""<style>{STORE_CSS}</style><script>
(function(){{
  var KEY={key}, BASE={json.dumps(base)};
  function load(){{try{{return JSON.parse(localStorage.getItem(KEY)||'{{}}')}}catch(e){{return {{}}}}}}
  function save(c){{try{{localStorage.setItem(KEY,JSON.stringify(c))}}catch(e){{}}count(c)}}
  function count(c){{var n=0;for(var k in c)n+=c[k];document.querySelectorAll('.vicinic-cart-count').forEach(function(el){{el.textContent=n}})}}
  count(load());
  document.querySelectorAll('.vicinic-add').forEach(function(b){{
    b.addEventListener('click',function(){{
      var c=load(),q=1,sel=b.getAttribute('data-qty-from');
      if(sel){{var inp=document.querySelector(sel);q=Math.max(1,Math.min(20,parseInt(inp&&inp.value||'1',10)||1))}}
      c[b.dataset.id]=Math.min(20,(c[b.dataset.id]||0)+q);save(c);b.textContent='Added ✓';
      setTimeout(function(){{b.textContent='Add to cart'}},1500);
    }});
  }});
  var lines=document.getElementById('vicinic-cart-lines');
  if(!lines)return;
  var form=document.getElementById('vicinic-checkout'),note=form.querySelector('.vicinic-checkout-note');
  function money(v){{return 'R'+Number(v).toFixed(2)}}
  function render(products){{
    var c=load(),html='',total=0,byId={{}};
    products.forEach(function(p){{byId[p.id]=p}});
    Object.keys(c).forEach(function(id){{
      var p=byId[id];if(!p){{delete c[id];return}}
      var sub=p.price*c[id];total+=sub;
      html+='<div class="vicinic-cart-row"><span>'+c[id]+' × '+p.name.replace(/</g,'&lt;')+'</span><span>'+money(sub)+' <button type="button" data-rm="'+id+'" aria-label="Remove">×</button></span></div>';
    }});
    save(c);
    lines.innerHTML=html?html+'<p class="fw-bold mt-2">Total: '+money(total)+'</p>':'<p class="text-muted">Your cart is empty.</p>';
    form.querySelector('button').disabled=!html;
    lines.querySelectorAll('[data-rm]').forEach(function(b){{b.addEventListener('click',function(){{var c=load();delete c[b.dataset.rm];save(c);render(products)}})}});
  }}
  fetch(BASE+'shop/data/').then(function(r){{return r.json()}}).then(function(d){{render(d.products)}});
  form.addEventListener('submit',function(e){{
    e.preventDefault();
    var c=load(),items=Object.keys(c).map(function(id){{return {{id:id,qty:c[id]}}}});
    var body={{items:items}};new FormData(form).forEach(function(v,k){{body[k]=v}});
    var btn=form.querySelector('button');btn.disabled=true;note.textContent='Starting secure payment…';
    fetch(BASE+'shop/checkout/',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify(body)}})
      .then(function(r){{return r.json().then(function(d){{if(!r.ok)throw new Error(d.error||'Something went wrong');return d}})}})
      .then(function(d){{
        var f=document.createElement('form');f.method='POST';f.action=d.process_url;
        d.fields.forEach(function(kv){{var i=document.createElement('input');i.type='hidden';i.name=kv[0];i.value=kv[1];f.appendChild(i)}});
        document.body.appendChild(f);f.submit();
      }})
      .catch(function(err){{note.textContent=err.message;btn.disabled=false}});
  }});
}})();
</script>"""
