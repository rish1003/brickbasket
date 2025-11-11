from django.contrib import admin
from .models import *

admin.site.register(User)
admin.site.register(Vendor)
admin.site.register(Product)
admin.site.register(Category)
admin.site.register(CartItem)
admin.site.register(Order)
admin.site.register(OrderItem)
