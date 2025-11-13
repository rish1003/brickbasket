"""
URL configuration for brickbasket project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from .views import *
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', landing, name="landing"),
    path('signup/', signup, name='signup'),
    path('signin/', signin, name='signin'),
    path('logout/', user_logout, name='logout'),
    path('admin_dashboard/', admin_dashboard, name='admin_dashboard'),
    path('admin_approve/<int:vendor_id>/', approve_vendor, name='approve_vendor'),
    path('admin_reject/<int:vendor_id>/', reject_vendor, name='reject_vendor'),
    path("admin_user/<int:user_id>/toggle/", toggle_user_status, name="toggle_user_status"),
    path('user/', user_main, name="user_main"),
    path('vendor/', vendor_main, name="vendor_main"),
    path('user/product', product_view, name="produSct"),
    path("cart/data/",get_cart, name="cart_data"),
    path("cart/add/", add_to_cart, name="add_to_cart"),
    path("cart/<int:item_id>/inc/", increment_cart_item, name="cart_inc"),
    path("cart/<int:item_id>/dec/", decrement_cart_item, name="cart_dec"),
    path("cart/<int:item_id>/delete/", delete_cart_item, name="cart_delete"),
    path("checkout/", checkout_page, name="checkout"),
    path("order/process/", process_order, name="process_order"),
    path("order/success/<int:order_id>/", order_success, name="order_success"),
    


] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

