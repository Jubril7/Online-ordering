from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, viewsets, generics, permissions
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly, IsAdminUser
from django_filters.rest_framework import DjangoFilterBackend
from django.utils.timezone import now, timedelta
from .serializers import ProductSerializer, CategorySerializer, CartSerializer, CartItemSerializer, RestaurantSerializer, DishSerializer
from django.db.models import Sum, Count


from django.shortcuts import get_object_or_404

from .models import Product, CartItem, Order, Category, Cart, CartItem, Restaurant, Dish

class CartView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        cart_items = CartItem.objects.filter(cart__user=request.user, is_ordered=False)
        cart_data = [
            {
                "id": item.id,
                "product": item.product.name,
                "price": item.product.price,
                "quantity": item.quantity,
                "total": item.product.price * item.quantity,
            }
            for item in cart_items
    ]
        return Response(cart_data, status=status.HTTP_200_OK)


class AddToCartView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        product_id = request.data.get("product_id")
        quantity = int(request.data.get("quantity", 1))

        if not product_id:
            return Response({"error": "Product ID is required."}, status=status.HTTP_400_BAD_REQUEST)

        product = get_object_or_404(Product, id=product_id)

        cart, _ = Cart.objects.get_or_create(user=request.user)
        cart_item, created = CartItem.objects.get_or_create(
        cart=cart,
        product=product,
        is_ordered=False
        )

        if not created:
            cart_item.quantity += quantity
        else:
            cart_item.quantity = quantity

        cart_item.save()

        return Response({"message": "Product added to cart."}, status=status.HTTP_200_OK)


class RemoveFromCartView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        item_id = request.data.get("item_id")
        if not item_id:
            return Response({"error": "Item ID is required."}, status=status.HTTP_400_BAD_REQUEST)

        cart = get_object_or_404(Cart, user=request.user)
        cart_item = get_object_or_404(CartItem, id=item_id, cart=cart, is_ordered=False)

        cart_item.delete()

        return Response({"message": "Item removed from cart."}, status=status.HTTP_200_OK)
    
    def delete(self, request):
        item_id = request.query_params.get("item_id")  # ✅ Changed from request.data to request.query_params

        if not item_id:
            return Response({"error": "Item ID is required."}, status=status.HTTP_400_BAD_REQUEST)

        cart = get_object_or_404(Cart, user=request.user)
        cart_item = get_object_or_404(CartItem, id=item_id, cart=cart, is_ordered=False)

        cart_item.delete()
        return Response({"message": "Item removed from cart."}, status=status.HTTP_200_OK)


class CheckoutView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        cart_items = CartItem.objects.filter(cart__user=request.user, is_ordered=False)

        if not cart_items.exists():
            return Response({"error": "Your cart is empty."}, status=status.HTTP_400_BAD_REQUEST)

        customer_profile = request.user.customerprofile
        order = Order.objects.create(customer=customer_profile)

        for item in cart_items:
            item.is_ordered = True
            item.order = order
            item.save()

        return Response({"message": "Order placed successfully."}, status=status.HTTP_201_CREATED)
    
class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['category'] 

class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer

class CartViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    def list(self, request):
        cart, _ = Cart.objects.get_or_create(user=request.user)
        serializer = CartSerializer(cart)
        return Response(serializer.data)

    def create(self, request):
        cart, _ = Cart.objects.get_or_create(user=request.user)
        product_id = request.data.get("product_id")
        quantity = int(request.data.get("quantity", 1))

        try:
            product = Product.objects.get(pk=product_id)
        except Product.DoesNotExist:
            return Response({"error": "Invalid product ID."}, status=400)

        item, created = CartItem.objects.get_or_create(cart=cart, product=product)
        if not created:
            item.quantity += quantity
        else:
            item.quantity = quantity
        item.save()

        return Response(CartItemSerializer(item).data, status=201)
class RestaurantCreateView(generics.CreateAPIView):
    queryset = Restaurant.objects.all()
    serializer_class = RestaurantSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

class RestaurantDetailView(generics.RetrieveUpdateAPIView):
    queryset = Restaurant.objects.all()
    serializer_class = RestaurantSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user.restaurant
    
class DishViewSet(viewsets.ModelViewSet):
    queryset = Dish.objects.all()
    serializer_class = DishSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
class TotalSalesReportView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        total = Order.objects.aggregate(total_sales=Sum('total_price'))['total_sales'] or 0
        return Response({"total_sales": total})


class OrderCountReportView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        count = Order.objects.count()
        return Response({"total_orders": count})
    
class TotalSalesReportView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        total = Order.objects.aggregate(total_sales=Sum('total_price'))['total_sales'] or 0
        return Response({"total_sales": total})


class TopDishesReportView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        dishes = Dish.objects.annotate(order_count=Count('order')).order_by('-order_count')[:5]
        data = [
            {
                "dish": dish.name,
                "order_count": dish.order_count
            }
            for dish in dishes
        ]
        return Response(data)


class DailyOrdersReportView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        today = now().date()
        last_7_days = [today - timedelta(days=i) for i in range(6, -1, -1)]

        data = []
        for day in last_7_days:
            count = Order.objects.filter(created_at__date=day).count()
            data.append({
                "date": day,
                "order_count": count
            })

        return Response(data)

class TopProductsView(APIView):
    def get(self, request):
        top_products = Product.objects.annotate(
            order_count=Count('orderitem')
        ).order_by('-order_count')[:5]

        data = [
            {
                'product': product.name,
                'order_count': product.order_count
            }
            for product in top_products
        ]
        return Response(data)

