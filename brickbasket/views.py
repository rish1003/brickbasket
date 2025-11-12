from django.shortcuts import render
from .decorators import *


def landing(request):
    #first page user sees + login and sign up
    return render(request, 'landing_login.html')
