from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ProductViewSet, CategoryViewSet, CartView, AddToCartView, RemoveFromCartView, CheckoutView, CartViewSet, RestaurantCreateView, RestaurantDetailView, DishViewSet, TotalSalesReportView, OrderCountReportView, TopDishesReportView, DailyOrdersReportView, TopProductsView
                    

router = DefaultRouter()
router.register(r'products', ProductViewSet)
router.register(r'categories', CategoryViewSet)
router.register(r'cart', CartViewSet, basename='cart')
router.register(r'dishes', DishViewSet, basename='dish')


urlpatterns = [
    path('', include(router.urls)),
    path('cart/', CartView.as_view()),
    path('cart/add/', AddToCartView.as_view()),
    path('cart/remove/', RemoveFromCartView.as_view()),
    path('cart/checkout/', CheckoutView.as_view()),
    path('restaurant/create/', RestaurantCreateView.as_view(), name='create-restaurant'),
    path('restaurant/me/', RestaurantDetailView.as_view(), name='my-restaurant'),
    path('reports/total-sales/', TotalSalesReportView.as_view()),
    path('reports/order-count/', OrderCountReportView.as_view()),
    path('reports/top-dishes/', TopDishesReportView.as_view()),
    path('reports/daily-orders/', DailyOrdersReportView.as_view()),
]
