from django.contrib import admin
from .models import Category, Product,Dish, CustomerProfile, RestaurantOwnerProfile

# Register your models here.

from django.contrib import admin
from .models import User, CustomerProfile, RestaurantOwnerProfile

admin.site.register(User)
admin.site.register(CustomerProfile)
admin.site.register(RestaurantOwnerProfile)
admin.site.register(Category)
admin.site.register(Product)
admin.site.register(Dish)

