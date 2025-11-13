from django.shortcuts import render, redirect
from django.urls import reverse
from .decorators import *
from django.http import JsonResponse
from django.contrib.auth import authenticate, login, logout
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.contrib.auth.hashers import make_password
from django.contrib.auth import get_user_model
import json
from .models import *


def landing(request):
    #first page user sees + login and sign up
    return render(request, 'landing_login.html')


@csrf_exempt
# we do this csrf exempt taaki security ki bt na ho nhi toh js mein karna padega cookies and shit
def signup(request):
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=400)
    
    data = json.loads(request.body.decode('utf-8')) #to get the data that we have passed form se

    username = data.get('username')
    email = data.get('email')
    password = data.get('password')
    first_name = data.get('first_name')
    last_name = data.get('last_name')
    role = data.get('role', 'customer')

    # extra fields only for vendor
    company_name = data.get('company_name')
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

def user_home(request, context):
    return  

@csrf_exempt
def user_login(request):
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=400)
    
    data = json.loads(request.body.decode('utf-8'))
    username_or_email = data.get('username')
    password = data.get('password')

    # Allow login by either username or email
    try:
        user_obj = User.objects.get(email=username_or_email)
        username = user_obj.username
    except User.DoesNotExist:
        username = username_or_email

    user = authenticate(request, username=username, password=password)

    if user is not None:
        login(request, user)
        return JsonResponse({"success": True, "username": user.username, "role": user.role})
    else:
        return JsonResponse({"error": "Invalid credentials"}, status=401)

@csrf_exempt
def user_logout(request):
    logout(request)
    return render(request, 'landing_login.html')
# def navbar(request):
#     #navbar
#     return render(request, 'user/navbar.html')

def user_main(request):
    #first page user sees after logging in
    return render(request, 'user/user_main.html')


def vendor_main(request):
    #first page user sees after logging in
    return render(request, 'vendor/vendor_main.html')

def product_view(request):
    #product details page, viewed on clicking a product card
    return render(request, 'user/product_view.html')

