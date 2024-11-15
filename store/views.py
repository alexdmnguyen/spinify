from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import Album, Cart, Order, CartItem, OrderItem, create_default_album
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.forms import AuthenticationForm 
from .forms import RegistrationForm
import base64
import requests
from requests.auth import HTTPBasicAuth
from django.shortcuts import redirect, render
from django.http import HttpResponse
from django.conf import settings
from django.contrib import messages
from datetime import datetime
from decimal import Decimal
from django import template

SPOTIFY_AUTH_URL = 'https://accounts.spotify.com/authorize'
SPOTIFY_TOKEN_URL = 'https://accounts.spotify.com/api/token'


def spotify_login(request):
    auth_url = f'{SPOTIFY_AUTH_URL}?client_id={settings.SPOTIFY_CLIENT_ID}&response_type=code&redirect_uri={settings.SPOTIFY_REDIRECT_URI}&scope=user-top-read'
    print("Spotify Login: Redirecting to Spotify authorization...")
    return redirect(auth_url)

def spotify_callback(request):
    print("Spotify Callback: Received authorization code...")
    code = request.GET.get('code')
    print(f"Spotify Callback: Received authorization code: {code}")

    token_data = {
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': settings.SPOTIFY_REDIRECT_URI,
    }

    headers = {
        'Authorization': f'Basic {base64.b64encode((settings.SPOTIFY_CLIENT_ID + ":" + settings.SPOTIFY_CLIENT_SECRET).encode()).decode()}',
    }

    response = requests.post(SPOTIFY_TOKEN_URL, data=token_data, headers=headers)

    if response.status_code == 200:
        access_token = response.json().get('access_token')
        request.session['spotify_access_token'] = access_token
        return redirect('home')  # Redirect to home page after successful Spotify authentication
    else:
        return HttpResponse('Spotify authentication failed.')


def landing(request):
    error_message = None  # Set this dynamically if needed

    context = {
        'error_message': error_message,  # Add this to your context
        # Add any other context data you need
    }

    return render(request, 'store/landing.html', context)

def home(request):
    if request.user.is_authenticated:
        create_default_album()

        spotify_access_token = request.session.get('spotify_access_token')

        if spotify_access_token:
            headers = {'Authorization': f'Bearer {spotify_access_token}'}

            profile_url = 'https://api.spotify.com/v1/me'
            response_profile = requests.get(profile_url, headers=headers)

            try:
                response_profile.raise_for_status()
            except requests.exceptions.HTTPError as err:
                print(f"Failed to fetch user profile from Spotify API: {err}")
                return render(request, 'store/home.html', {'error_message': 'Failed to fetch user profile from Spotify API'})

            user_name = response_profile.json().get('display_name', 'Spotify User')

            time_range = request.GET.get('time_range', 'long_term')
            top_tracks_url = f'https://api.spotify.com/v1/me/top/tracks?limit=50&time_range={time_range}'

            response_tracks = requests.get(top_tracks_url, headers=headers)

            try:
                response_tracks.raise_for_status()
            except requests.exceptions.HTTPError as err:
                print(f"Failed to fetch data from Spotify API: {err}")
                return render(request, 'store/home.html', {'error_message': 'Failed to fetch data from Spotify API'})

            top_tracks = response_tracks.json().get('items', [])
            seen_albums = set()  # Keep track of seen Spotify IDs
            top_albums = []

            for track in top_tracks:
                album_data = track['album']
                spotify_id = album_data['id']

                album, created = Album.objects.get_or_create(
                    spotify_id=spotify_id,
                    defaults={
                        'title': album_data['name'],
                        'artist': album_data['artists'][0]['name'],
                        'cover_url': album_data['images'][0]['url'] if album_data['images'] else None,
                        'price': 9.99,  # Set a default price or fetch it from somewhere
                    }
                )

                if created and request.user.is_authenticated:
                    album.added_by = request.user
                    album.save()

                if spotify_id in seen_albums:
                    continue

                seen_albums.add(spotify_id)

                album_data['cover_url'] = album.cover_url if album.cover_url else None
                album_data['title'] = album.title
                album_data['price'] = album.price

                top_albums.append(album_data)

            # print("Top Albums:", top_albums)

            return render(request, 'store/home.html', {'top_tracks': top_tracks, 'top_albums': top_albums, 'user_name': user_name})
        else:
            try:
                default_album = Album.objects.get(title='Default Album')
            except Album.DoesNotExist:
                default_album = None

            return render(request, 'store/home.html', {'default_album_data': default_album})
    else:
        # If user is not authenticated, render the landing page
        return render(request, 'store/register.html')


def register_view(request):
    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('home')
    else:
        form = RegistrationForm()

    return render(request, 'store/register.html', {'form': form})

def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, request.POST)  # Use AuthenticationForm
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            
            user = authenticate(request, username=username, password=password)

            if user is not None:
                login(request, user)
                return redirect('home')  # Redirect to home page after successful login
            else:
                # Handle invalid login credentials (you can customize this part)
                return render(request, 'store/login.html', {'form': form, 'error_message': 'Invalid username or password'})
        else:
            # Handle form validation errors
            return render(request, 'store/login.html', {'form': form, 'error_message': 'Invalid form submission'})

    else:
        form = AuthenticationForm()  # Create a new instance of AuthenticationForm

    return render(request, 'store/login.html', {'form': form})

@login_required
def logout_view(request):
    logout(request)
    return redirect('landing')  # Redirect to home page after logout

@login_required
def cart(request):
    try:
        user_cart = Cart.objects.get(user=request.user)
        cart_items = user_cart.cartitem_set.all()

        # Calculate and set total price for each item
        for item in cart_items:
            item.total_item_price = Decimal(item.album.price) * item.quantity
            item.save()

        total_price = sum(item.total_item_price for item in cart_items)
    except Cart.DoesNotExist:
        user_cart = None
        total_price = Decimal(0)

    return render(request, 'store/cart.html', {'cart': user_cart, 'total_price': total_price})

@login_required
def checkout(request):
    user_cart = Cart.objects.get(user=request.user)

    if user_cart.cartitem_set.exists():
        total_price = sum(item.album.price * item.quantity for item in user_cart.cartitem_set.all())
        return render(request, 'store/checkout.html', {'cart': user_cart, 'total_price': total_price})
    else:
        messages.error(request, 'Your cart is empty. Add items to your cart before checking out.')
        return redirect('cart')

@login_required
def profile(request):
    user_orders = Order.objects.filter(user=request.user)
    return render(request, 'store/profile.html', {'orders': user_orders})

@login_required
def add_to_cart(request, album_id):
    if request.method == 'POST':
        try:
            # Convert album_id to string
            album_id_str = str(album_id)

            # Try to get the Album with the converted album_id_str
            album = Album.objects.get(pk=album_id_str)

            # Get the user's cart or create a new one if it doesn't exist
            cart, created = Cart.objects.get_or_create(user=request.user)

            # Try to get the CartItem with the given album in the cart
            cart_items = CartItem.objects.filter(cart=cart, album=album)

            if cart_items.exists():
                # If the item exists, update the quantity based on the form input
                quantity = int(request.POST.get('quantity', 1))
                cart_item = cart_items.first()
                cart_item.quantity += quantity
                cart_item.save()
                messages.success(request, f'Updated quantity to {cart_item.quantity} for {album.title}.')
            else:
                # If the item doesn't exist, create a new CartItem with quantity based on the form input
                quantity = int(request.POST.get('quantity', 1))
                messages.success(request, f'{album.title} added to your cart!')
                CartItem.objects.create(cart=cart, album=album, quantity=quantity)

            return redirect('home')  # Redirect to the home page or any other desired page
        except Album.DoesNotExist:
            messages.error(request, 'Album does not exist.')
    else:
        messages.error(request, 'Invalid request.')

    return redirect('home')  # Redirect to the home page or any other desired page

@login_required
def clear_cart(request):
    # Get the user's cart
    cart = Cart.objects.get(user=request.user)

    # Delete all cart items related to the user's cart
    CartItem.objects.filter(cart=cart).delete()

    # Optionally, you can redirect the user to the cart page or any other page
    return redirect('cart')

@login_required
def confirm_checkout(request):
    user_cart = Cart.objects.get(user=request.user)

    if user_cart.cartitem_set.exists():
        # Process the confirmation logic here
        # For example, you can move the cart items to the order database table
        # and then clear the cart.
        total_price = sum(item.album.price * item.quantity for item in user_cart.cartitem_set.all())
        order = Order.objects.create(user=request.user, total_price=total_price)

        first_name = request.POST.get('first_name', '')
        order.first_name = first_name

        middle_name = request.POST.get('middle_name', '')
        order.middle_name = middle_name

        last_name = request.POST.get('last_name', '')
        order.last_name = last_name
        
        # Save shipping address
        shipping_address = request.POST.get('shipping_address', '')
        order.shipping_address = shipping_address

        city = request.POST.get('city', '')
        order.city = city

        state = request.POST.get('state', '')
        order.state = state

        country = request.POST.get('country','')
        order.country = country

        # Save credit card information
        credit_card_number = request.POST.get('credit_card_number', '')
        order.credit_card_number = credit_card_number
        
        # Save only the last 4 digits of the credit card number
        last_4_digits = credit_card_number[-4:]
        order.credit_card_last_4_digits = last_4_digits

        order.save()

        for item in user_cart.cartitem_set.all():
            OrderItem.objects.create(order=order, album=item.album, quantity=item.quantity)

        # Clear the user's cart after checkout
        user_cart.albums.clear()

        return render(request, 'store/order_success.html', {'order': order})
    else:
        messages.error(request, 'Cannot confirm checkout with an empty cart. Add items to your cart before checking out.')
        return redirect('cart')

@login_required
def add_default_to_cart(request):
    # Add the default album to the cart
    try:
        default_album = Album.objects.get(title='Default Album')
        cart, created = Cart.objects.get_or_create(user=request.user)
        cart_item, created = CartItem.objects.get_or_create(cart=cart, album=default_album)
        
        if not created:
            # If the item already exists, increase the quantity
            cart_item.quantity += 1
            cart_item.save()

        messages.success(request, f'{default_album.title} added to your cart!')
        return redirect('home')  # Redirect to the home page or any other desired page

    except Album.DoesNotExist:
        messages.error(request, 'Default Album does not exist.')
        return redirect('home')  # Redirect to the home page or any other desired page

@login_required
def remove_from_cart(request, album_id):
    cart = request.user.cart

    # Convert album_id to string
    album_id_str = str(album_id)

    # Try to get the Album with the converted album_id_str
    album = Album.objects.get(pk=album_id_str)

    # album = get_object_or_404(Album, id=album_id)

    # Remove the item from the cart
    cart_item = CartItem.objects.filter(cart=cart, album=album).first()
    if cart_item:
        cart_item.delete()

    return redirect('cart')

@login_required
def update_cart(request):
    if request.method == 'POST':
        # Get the user's cart
        user_cart = request.user.cart

        # Iterate through form data to update quantities
        for key, value in request.POST.items():
            if key.startswith('quantity_'):
                album_spotify_id = key.replace('quantity_', '')
                try:
                    quantity = int(value)
                    if quantity == 0:
                        # Remove the item if quantity is 0
                        CartItem.objects.filter(cart=user_cart, album__spotify_id=album_spotify_id).delete()
                    else:
                        # Update the quantity for the corresponding CartItem
                        cart_item = CartItem.objects.get(cart=user_cart, album__spotify_id=album_spotify_id)
                        cart_item.quantity = quantity
                        cart_item.save()
                except (ValueError, CartItem.DoesNotExist):
                    messages.error(request, 'Invalid quantity update.')

        messages.success(request, 'Cart updated successfully.')

    return redirect('cart')  # Redirect back to the cart page

SPOTIFY_ALBUM_URL = 'https://api.spotify.com/v1/albums/{album_id}'

@login_required
def product_page(request, album_id):
    album_id_str = str(album_id)
    album = get_object_or_404(Album, pk=album_id_str)

    spotify_access_token = request.session.get('spotify_access_token')

    if spotify_access_token:
        headers = {'Authorization': f'Bearer {spotify_access_token}'}
        album_url = SPOTIFY_ALBUM_URL.format(album_id=album.spotify_id)
        response_album = requests.get(album_url, headers=headers)

        try:
            response_album.raise_for_status()
            album_details = response_album.json()
        except requests.exceptions.HTTPError as err:
            print(f"Failed to fetch album details from Spotify API: {err}")
            return render(request, 'store/product_page.html', {'error_message': 'Failed to fetch album details from Spotify API'})

        # Format release date
        release_date = datetime.strptime(album_details['release_date'], '%Y-%m-%d').strftime('%B %d, %Y')

        # Set description based on total tracks
        if album_details['total_tracks'] == 1:
            description = None
        else:
            description = f"This album has {album_details['total_tracks']} total tracks."

        if album_details['total_tracks'] > 1:
            description = f"This album has {album_details['total_tracks']} total tracks."

        # Get tracklist if album has more than one track
        tracklist = None
        if album_details['total_tracks'] > 1:
            tracklist = album_details['tracks']['items']

        # Fix Spotify link
        spotify_link = album_details['external_urls']['spotify']

        context = {
            'album': album,
            'album_details': album_details,
            'release_date': release_date,
            'description': description,
            'tracklist': tracklist,
            'spotify_link': spotify_link,
        }

        return render(request, 'store/product_page.html', context)
    else:
        return HttpResponse('Spotify access token not found.')
    
register = template.Library()

@register.filter(name='cart_item_count')
def cart_item_count(user):
    try:
        user_cart = user.cart
        total_item_count = sum(item.quantity for item in user_cart.cartitem_set.all())
        return total_item_count
    except AttributeError:
        return 0  # Return 0 if the user does not have a cart



