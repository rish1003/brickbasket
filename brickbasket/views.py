from django.shortcuts import render, redirect,get_object_or_404
from django.urls import reverse
from .decorators import *
from django.http import JsonResponse
from django.contrib.auth import authenticate, login, logout
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.contrib.auth.hashers import make_password
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
import json
from .models import *
from django.db.models.functions import TruncMonth
from django.db.models import Count
from django.utils.text import slugify
from django.db import transaction

def landing(request):
    if request.user.is_authenticated:
        print(request.user.role)
        if request.user.role == "admin":
            return redirect("admin_dashboard")

        if request.user.role == "vendor":
            return redirect("vendor_main")

        if request.user.role == "customer":
            return redirect("user_main")

    return render(request, 'landing_login.html')


def generate_username(company_name):
    base = slugify(company_name)[:20]  # safe, URL-like, lowercase
    existing = User.objects.filter(username__startswith=base).count()
    return f"{base}-{existing+1:03d}"

@csrf_exempt
# we do this csrf exempt taaki security ki bt na ho nhi toh js mein karna padega cookies and shit
def signup(request):
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=400)
    
    data = json.loads(request.body.decode('utf-8')) #to get the data that we have passed form se

    
    email = data.get('email')
    password = data.get('password')
    first_name = data.get('first_name')
    last_name = data.get('last_name')
    if first_name:
        username = generate_username(first_name+" "+last_name)
    role = data.get('role', 'customer')

    # extra fields only for vendor
    company_name = data.get('company_name')
    if company_name:
        print(company_name)
        username=generate_username(company_name)
        first_name = last_name = company_name
    gst_number = data.get('gst_number')
    
    print(data)

    # ---- Validation ----
    if not all([username, email, password]):
        return JsonResponse({"error": "Missing required fields"}, status=400)

    if User.objects.filter(username=username).exists():
        return JsonResponse({"error": "Username already exists"}, status=400)
    if User.objects.filter(email=email).exists():
        return JsonResponse({"error": "Email already exists"}, status=400)

    # ---- Create User ----
    user = User.objects.create(
        username=username,
        email=email,
        first_name=first_name,
        last_name=last_name,
        password=make_password(password),
        role=role,
        status='active'
    )
    # status = active means ki bande ka account is allowed in system, verification is for vendor only toh woh vendor model and by default false
    # ---- Create Vendor Profile if vendor ----
    if role == "vendor":
        if not company_name or not gst_number:
            user.delete()  # rollback if vendor data missing
            return JsonResponse({"error": "Missing vendor details"}, status=400)

        vendor = Vendor.objects.create(
            user=user,
            company_name=company_name,
            gst_number=gst_number,
            verified=False
        )

    # log the user in 
    login(request, user) #django sec defined method

    # ---- Redirect Based on Role ----
    if role == "vendor":
        target_url = reverse(vendor_main) # Use reverse to get the URL
    elif role == "customer":
        target_url = reverse(user_main)
    else:
        return JsonResponse({
        "success": False, 
        "error": "error occurred",
        }, status=404)

    return JsonResponse({
        "success": True, 
        "message": "Signup successful",
        "redirect_url": target_url
    }, status=200)


@csrf_exempt
def signin(request):
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=400)
    
    data = json.loads(request.body.decode('utf-8'))
    username_or_email = data.get('username')
    password = data.get('password')
    role = data.get('role')

    # Allow login by either username or email
    if username_or_email != "admin":
        try:
            user_obj = User.objects.get(email=username_or_email)
            username = user_obj.username
        except User.DoesNotExist:
            username = username_or_email
    else:
        username = "admin"
        password = "admin"
        role = "admin"

    user = authenticate(request, username=username, password=password)
    print(user)

    if user is not None:
        
        login(request, user)
        if role == "vendor":
            target_url = reverse(vendor_main) 
        elif role == "customer":
            target_url = reverse(user_main)
        elif role == "admin":
            target_url = reverse(admin_dashboard)
        else:
            return JsonResponse({
            "success": False, 
            "error": "error occurred",
            }, status=404)

        return JsonResponse({"success": True, "username": user.username, "role": user.role, "redirect_url": target_url})
    else:
        return JsonResponse({"error": "Invalid credentials"}, status=401)

@csrf_exempt
def user_logout(request):
    logout(request)
    return redirect(landing)
# def navbar(request):
#     #navbar
#     return render(request, 'user/navbar.html')

def user_main(request):
    #first page user sees after logging in
    return render(request, 'user/user_main.html')


def vendor_main(request):
    #first page user sees after logging in
    return render(request, 'vendor/dashboard.html')

def admin_main(request):
    #first page user sees after logging in
    return render(request, 'admin/admin_main.html')

def product_view(request):
    #product details page, viewed on clicking a product card
    return render(request, 'user/product_view.html')



@csrf_exempt 
def approve_vendor(request, vendor_id):
    try:
        vendor = Vendor.objects.get(pk=vendor_id)
        vendor.verified = True
        vendor.save()

        vendor.user.status = "active"
        vendor.user.save()

        return reverse(admin_dashboard)
    except Vendor.DoesNotExist:
        return JsonResponse({"error": "Vendor not found"}, status=404)
 
@csrf_exempt   
def reject_vendor(request, vendor_id):
    try:
        vendor = Vendor.objects.get(pk=vendor_id)

        vendor.user.status = "disabled"
        vendor.user.save()

        vendor.delete()  # removes vendor entry

        return reverse(admin_dashboard)
    except Vendor.DoesNotExist:
        return JsonResponse({"error": "Vendor not found"}, status=404)
    
@csrf_exempt
def toggle_user_status(request, user_id):


    user = get_object_or_404(User, id=user_id)
    user.is_active = not user.is_active
    user.save()

    return redirect("admin_dashboard")
def calculate_percentage_change(current, previous):
    if previous == 0:
        if current == 0:
            return {"value": "0%", "class": ""}
        return {"value": "+100%", "class": "positive"}

    change = ((current - previous) / previous) * 100
    formatted = f"{change:+.1f}%"
    css_class = "positive" if change > 0 else "negative" if change < 0 else ""

    return {"value": formatted, "class": css_class}


# --------------------------
# Helper: last 6 month labels
# --------------------------
def last_6_month_labels():
    today = timezone.now().date()
    labels = []
    for i in range(6):
        m = (today - timedelta(days=30 * (5 - i))).strftime("%b")
        labels.append(m)
    return labels


def admin_dashboard(request):
    today = timezone.now().date()
    first_day_this_month = today.replace(day=1)
    first_day_last_month = (first_day_this_month - timedelta(days=1)).replace(day=1)

    # -------------------------
    # TOTAL USERS & GROWTH
    # -------------------------
    total_users = User.objects.count()

    users_this_month = User.objects.filter(date_joined__gte=first_day_this_month).count()
    users_last_month = User.objects.filter(
        date_joined__gte=first_day_last_month,
        date_joined__lt=first_day_this_month
    ).count()

    user_growth = calculate_percentage_change(users_this_month, users_last_month)

    # -------------------------
    # USER GROWTH CHART (last 6 months)
    # -------------------------
    user_qs = (
        User.objects.annotate(month=TruncMonth("date_joined"))
        .values("month")
        .annotate(count=Count("id"))
        .order_by("month")
    )

    user_growth_labels = []
    user_growth_data = []
    for entry in user_qs:
        user_growth_labels.append(entry["month"].strftime("%b"))
        user_growth_data.append(entry["count"])

    # fallback → prevents chart 400 errors
    if not user_growth_labels:
        user_growth_labels = last_6_month_labels()
        user_growth_data = [0] * 6

    # -------------------------
    #  ACTIVE VENDORS & GROWTH
    # -------------------------
    active_vendors = Vendor.objects.filter(verified=True).count()
    pending_vendors_count = Vendor.objects.filter(verified=False).count()
    inactive_vendors_count = Vendor.objects.filter(verified=False).count()  # adjust if needed

    vendors_this_month = Vendor.objects.filter(
        user__date_joined__gte=first_day_this_month
    ).count()

    vendors_last_month = Vendor.objects.filter(
        user__date_joined__gte=first_day_last_month,
        user__date_joined__lt=first_day_this_month
    ).count()

    vendor_growth = calculate_percentage_change(vendors_this_month, vendors_last_month)

    # -------------------------
    # VENDOR DISTRIBUTION CHART
    # -------------------------
    vendor_distribution = [
        active_vendors,
        pending_vendors_count,
        inactive_vendors_count
    ]

    # -------------------------
    #  TOTAL ORDERS & GROWTH
    # -------------------------
    total_orders = Order.objects.filter(payment_status="paid").count()

    orders_this_month = Order.objects.filter(
        created_at__gte=first_day_this_month,
        payment_status="paid"
    ).count()

    orders_last_month = Order.objects.filter(
        created_at__gte=first_day_last_month,
        created_at__lt=first_day_this_month,
        payment_status="paid"
    ).count()

    order_growth = calculate_percentage_change(orders_this_month, orders_last_month)

    # -------------------------
    #ORDER STATS CHART (last 6 months)
    # -------------------------
    order_qs = (
        Order.objects.filter(payment_status='paid')
        .annotate(month=TruncMonth("created_at"))
        .values("month")
        .annotate(count=Count("order_id"))
        .order_by("month")
    )

    order_stats_labels = []
    order_stats_data = []

    for entry in order_qs:
        order_stats_labels.append(entry["month"].strftime("%b"))
        order_stats_data.append(entry["count"])

    if not order_stats_labels:
        order_stats_labels = last_6_month_labels()
        order_stats_data = [0] * 6

    # -------------------------
    # REVENUE (last 6 months)
    # -------------------------
    six_months_ago = today - timedelta(days=180)

    revenue_qs = (
        Order.objects.filter(payment_status='paid', created_at__date__gte=six_months_ago)
        .annotate(month=TruncMonth("created_at"))
        .values("month")
        .annotate(total=Sum("total_amount"))
        .order_by("month")
    )

    revenue_labels = []
    revenue_data = []

    for entry in revenue_qs:
        revenue_labels.append(entry["month"].strftime("%b"))
        revenue_data.append(round(float(entry["total"]) / 100000, 2))  # convert to lakhs

    if not revenue_labels:
        revenue_labels = last_6_month_labels()
        revenue_data = [0] * 6

    # ------------------------------------------------
    # RENDER
    # ------------------------------------------------
    return render(request, "admin/dashboard.html", {
        "total_users": total_users,
        "active_vendors": active_vendors,
        "pending_vendors": pending_vendors_count,
        "total_orders": total_orders,

        # Growth
        "user_growth": user_growth["value"],
        "user_growth_class": user_growth["class"],

        "vendor_growth": vendor_growth["value"],
        "vendor_growth_class": vendor_growth["class"],

        "order_growth": order_growth["value"],
        "order_growth_class": order_growth["class"],

        # lists
        "pending_vendor_list": Vendor.objects.filter(verified=False),
        "all_users": User.objects.all(),

        # Charts
        "user_growth_labels": user_growth_labels,
        "user_growth_data": user_growth_data,

        "order_stats_labels": order_stats_labels,
        "order_stats_data": order_stats_data,

        "vendor_distribution": vendor_distribution,

        "revenue_labels": revenue_labels,
        "revenue_data": revenue_data,
    })


@transaction.atomic
def add_to_cart(request):
    user = request.user
    data = json.loads(request.body)

    product_id = data.get("product_id")
    quantity = int(data.get("quantity", 1))

    product = Product.objects.select_for_update().get(id=product_id)

    if product.stock < quantity:
        return JsonResponse({"error": "Not enough stock"}, status=400)

    cart_item, created = CartItem.objects.get_or_create(
        user=user, product=product,
        defaults={"quantity": 0}
    )

    cart_item.quantity += quantity
    cart_item.save()

    product.stock -= quantity
    product.save()

    return JsonResponse({"success": True})

def get_cart(request):
    user = request.user
    items = CartItem.objects.filter(user=user).select_related("product")

    data = {
        "count": items.count(),
        "total": sum(i.subtotal for i in items),
        "items": [
            {
                "cart_item_id": i.cart_item_id,
                "name": i.product.name,
                "image": i.product.image.url if i.product.image else "",
                "quantity": i.quantity,
                "subtotal": float(i.subtotal),
            }
            for i in items
        ],
    }
    return JsonResponse(data)

@csrf_exempt
@transaction.atomic
def increment_cart_item(request, item_id):
    cart_item = CartItem.objects.select_related("product").select_for_update().get(cart_item_id=item_id)
    product = cart_item.product

    if product.stock <= 0:
        return JsonResponse({"error": "Out of stock"}, status=400)

    cart_item.quantity += 1
    cart_item.save()

    product.stock -= 1
    product.save()

    user = request.user
    items = CartItem.objects.filter(user=user).select_related("product")

    data = {
        "count": items.count(),
        "total": sum(i.subtotal for i in items),
        "items": [
            {
                "cart_item_id": i.cart_item_id,
                "name": i.product.name,
                "image": i.product.image.url if i.product.image else "",
                "quantity": i.quantity,
                "subtotal": float(i.subtotal),
            }
            for i in items
        ],
    }
    return JsonResponse(data)

@csrf_exempt
@transaction.atomic
def decrement_cart_item(request, item_id):
    cart_item = CartItem.objects.select_related("product").select_for_update().get(cart_item_id=item_id)
    product = cart_item.product

    cart_item.quantity -= 1
    product.stock += 1

    if cart_item.quantity == 0:
        cart_item.delete()
    else:
        cart_item.save()

    product.save()

    user = request.user
    items = CartItem.objects.filter(user=user).select_related("product")

    data = {
        "count": items.count(),
        "total": sum(i.subtotal for i in items),
        "items": [
            {
                "cart_item_id": i.cart_item_id,
                "name": i.product.name,
                "image": i.product.image.url if i.product.image else "",
                "quantity": i.quantity,
                "subtotal": float(i.subtotal),
            }
            for i in items
        ],
    }
    return JsonResponse(data)


@csrf_exempt
@transaction.atomic
def delete_cart_item(request, item_id):
    cart_item = CartItem.objects.select_related("product").select_for_update().get(cart_item_id=item_id)
    product = cart_item.product

    product.stock += cart_item.quantity
    product.save()

    cart_item.delete()

    return JsonResponse({"success": True})

def checkout_page(request):
    user = request.user


    if not user.is_authenticated:
        return redirect("signin")


    cart_items = CartItem.objects.filter(user=user).select_related("product")

    if not cart_items.exists():
        return redirect("user_main")  

    subtotal = sum(i.product.price * i.quantity for i in cart_items)
    shipping = 0  # free
    total = subtotal + shipping

    return render(request, "user/checkout.html", {
        "cart_items": cart_items,
        "subtotal": subtotal,
        "total": total,
    })

@csrf_exempt
@transaction.atomic
def process_order(request):
    if request.method != "POST":
        return redirect("checkout")

    user = request.user
    cart_items = CartItem.objects.select_for_update().filter(user=user)

    if not cart_items.exists():
        return redirect("checkout")

    for item in cart_items:
        if item.product.stock < item.quantity:
            return render(request, "user/checkout.html", {
                "cart_items": cart_items,
                "subtotal": sum(i.product.price * i.quantity for i in cart_items),
                "total": sum(i.product.price * i.quantity for i in cart_items),
                "error": f"Not enough stock for {item.product.name}",
            })

    subtotal = sum(i.product.price * i.quantity for i in cart_items)
    order = Order.objects.create(
        user=user,
        total_amount=subtotal,
        payment_status="paid",
        order_status="placed",
    )
    for item in cart_items:
        OrderItem.objects.create(
            order=order,
            product=item.product,
            quantity=item.quantity,
            unit_price=item.product.price
        )
    cart_items.delete()

    return redirect("order_success", order_id=order.order_id)

def order_success(request, order_id):
    order = get_object_or_404(Order, order_id=order_id, user=request.user)

    items = order.items.select_related("product")

    total_items = sum(i.quantity for i in items)

    return render(request, "user/checkout_success.html", {
        "order": order,
        "items": items,
        "total_items": total_items,
        "order_id": order.order_id,
        "total": order.total_amount,
        "payment_status": order.payment_status,
        "order_status": order.order_status,
    })

def order_dashboard(request):
    new_orders = Order.objects.filter(order_status='placed').count()
    shipped_orders = Order.objects.filter(order_status='dispatched').count()
    delivered_orders = Order.objects.filter(order_status='delivered').count()

    context = {
        'new_orders': new_orders,
        'shipped_orders': shipped_orders,
        'delivered_orders': delivered_orders,
    }
    return render(request, 'vendor/dashboard.html', context)
def management(request):
    vendor = Vendor.objects.get(user=request.user.id)
    items = Product.objects.filter(vendor=vendor)
    return render(request, "vendor/inventory.html", {"items": items})   

# ---------- ADD ITEM ----------
def add_item(request):
    vendor = Vendor.objects.get(user=request.user)
    categories = Category.objects.all()  # to show in dropdown

    if request.method == "POST":
        name = request.POST.get("name")
        description = request.POST.get("description")
        category_id = request.POST.get("category")
        price = request.POST.get("price")
        unit = request.POST.get("unit")
        stock = request.POST.get("stock")
        image = request.FILES.get("image")

        category = Category.objects.get(id=category_id)

        Product.objects.create(
            vendor=vendor,
            name=name,
            description=description,
            category=category,
            price=price,
            unit=unit,
            stock=stock,
            image=image
        )

        return redirect("management")   # your vendor dashboard

    return render(request, "vendor/add_item.html", {"categories": categories})

# ---------- EDIT ITEM ----------
def edit_item(request, product_id):
    vendor = Vendor.objects.get(user=request.user)
    product = Product.objects.get(product_id=product_id, vendor=vendor)
    categories = Category.objects.all()

    if request.method == "POST":
        product.name = request.POST.get("name")
        product.description = request.POST.get("description")

        category_id = request.POST.get("category")
        product.category = Category.objects.get(id=category_id)

        product.price = request.POST.get("price")
        product.unit = request.POST.get("unit")
        product.stock = request.POST.get("stock")

        # If new image uploaded, replace old one
        if "image" in request.FILES:
            product.image = request.FILES["image"]

        product.save()
        return redirect("management")

    return render(request, "vendor/edit_item.html", {
        "product": product,
        "categories": categories
    })

# ---------- DELETE ITEM ----------
def delete_item(request, product_id):
    vendor = Vendor.objects.get(user=request.user)
    product = Product.objects.get(product_id=product_id, vendor=vendor)

    if request.method == "POST":
        product.delete()
        return redirect("management")

    return render(request, "vendor/delete_item_confirm.html", {"product": product})
'''def a(request):
    order_counts = Order.objects.filter(order_status="placed")
    context={
        'order_counts':order_counts,
    }
    return render(request, "vendor/dashboard.html", context)
    
'''