from django.urls import path
from .views import landing, home, cart, checkout, product_page, confirm_checkout, add_default_to_cart, profile, add_to_cart, update_cart, clear_cart, remove_from_cart, login_view, logout_view, register_view, spotify_login, spotify_callback

urlpatterns = [
    path('', landing, name='landing'),
    path('home', home, name='home'),
    path('cart/', cart, name='cart'),
    path('checkout/', checkout, name='checkout'),
    path('profile/', profile, name='profile'),
    path('add_to_cart/<str:album_id>/', add_to_cart, name='add_to_cart'),
    path('clear_cart/', clear_cart, name='clear_cart'),  # Make sure this line is correct
    path('login/', login_view, name='login'),
    path('logout/', logout_view, name='logout'),
    path('register/', register_view, name='register'),
    path('spotify/login/', spotify_login, name='spotify_login'),
    path('spotify/callback/', spotify_callback, name='spotify_callback'),
    path('confirm_checkout/', confirm_checkout, name='confirm_checkout'),
    path('add_default_to_cart/', add_default_to_cart, name='add_default_to_cart'),
    path('update_cart/', update_cart, name='update_cart'),
    path('remove_from_cart/<str:album_id>/', remove_from_cart, name='remove_from_cart'),
    path('product/<str:album_id>/', product_page, name='product_page'),
]