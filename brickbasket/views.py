from django.shortcuts import render
from .decorators import *


def landing(request):
    #first page user sees + login and sign up
    return render(request, 'landing_login.html')

# def navbar(request):
#     #navbar
#     return render(request, 'user/navbar.html')

def user_main(request):
    #first page user sees after liging in
    return render(request, 'user/user_main.html')


def product_view(request):
    #product details page, viewed on clicking a product card
    return render(request, 'user/product_view.html')

