from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, viewsets, generics, permissions, serializers
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly, IsAdminUser
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.exceptions import PermissionDenied
from django.utils.timezone import now, timedelta
from .serializers import ProductSerializer, CategorySerializer, CartSerializer, CartItemSerializer, RestaurantSerializer, DishSerializer, RestaurantSerializer, OrderSerializer
from django.db.models import Sum, Count


from django.shortcuts import get_object_or_404

from .models import Product, CartItem, Order, Category, Cart, CartItem, Restaurant, Dish, RestaurantOwnerProfile

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
        user = self.request.user
        if Restaurant.objects.filter(owner=user).exists():
            raise serializers.ValidationError("You already have a restaurant.")
        serializer.save(owner=user)

class RestaurantDetailView(generics.RetrieveUpdateAPIView):
    queryset = Restaurant.objects.all()
    serializer_class = RestaurantSerializer
    permission_classes = [IsAuthenticated]

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
        total_sales = Order.objects.aggregate(total_sales=Sum('total_price'))['total_sales'] or 0
        return Response({
            "total_orders": count,
            "total_sales": total_sales
    })


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
    permission_classes = [IsAdminUser]
    def get(self, request):
        top_products = Product.objects.annotate(
            order_count=Count('order_items')
        ).order_by('-order_count')[:5]

        serializer = ProductSerializer(top_products, many=True)
        return Response(serializer.data)

        # data = [
        #     {
        #         'product': product.name,
        #         'order_count': product.order_count
        #     }
        #     for product in top_products
        # ]
        # return Response(data)

class MyOrdersView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        customer_profile = request.user.customerprofile
        orders = Order.objects.filter(customer=customer_profile).order_by('-created_at')
        serializer = OrderSerializer(orders, many=True)
        return Response(serializer.data)
    
class RestaurantOrdersAPIView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            restaurant = RestaurantOwnerProfile.objects.get(user=request.user)
        except RestaurantOwnerProfile.DoesNotExist:
            raise PermissionDenied("You are not a restaurant owner.")

        today = now().date()

        orders = Order.objects.filter(
            restaurant=restaurant,
            created_at__date=today
        )

        serializer = OrderSerializer(orders, many=True)
        return Response(serializer.data)
        
# class MyOrdersView(APIView):
#     authentication_classes = [TokenAuthentication]
#     permission_classes = [IsAuthenticated]

#     def get(self, request):
#         customer_profile = request.user.customerprofile
#         orders = Order.objects.filter(customer=customer_profile).order_by('-created_at')
#         serializer = OrderSerializer(orders, many=True)
#         return Response(serializer.data)

