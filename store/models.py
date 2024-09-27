from django.db import models
from django.contrib.auth.models import User
from .fields import CharFieldPrimaryKey

class Album(models.Model):
    spotify_id = models.CharField(max_length=255, primary_key=True, default='')
    title = models.CharField(max_length=255)
    artist = models.CharField(max_length=255)
    cover_url = models.URLField(blank=True, null=True)
    price = models.DecimalField(max_digits=6, decimal_places=2)
    added_by = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    is_default = models.BooleanField(default=False)

def create_default_album():
    default_album, created = Album.objects.update_or_create(
        spotify_id='default',  
        defaults={
            'title': 'Nothing Was The Same',
            'artist': 'Drake',
            'cover_url': 'https://www.udiscovermusic.com/wp-content/uploads/2018/09/Drake-Nothing-Was-The-Same-deluxe-album-cover-web-optimised-820-820x820.jpg',  
            'price': 9.99,
            'is_default': True  
        }
    )

class Cart(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    albums = models.ManyToManyField(Album, through='CartItem')

class CartItem(models.Model):
    album = models.ForeignKey(Album, on_delete=models.CASCADE)
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    total_item_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)  

class Order(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    albums = models.ManyToManyField(Album, through='OrderItem')
    total_price = models.DecimalField(max_digits=8, decimal_places=2)
    
    shipping_address = models.CharField(max_length=255, default='')
    credit_card_number = models.CharField(max_length=16, default='0000000000000000', null=True, blank=True)
    credit_card_last_4_digits = models.CharField(max_length=4, default='0000', null=True, blank=True)


class OrderItem(models.Model):
    album = models.ForeignKey(Album, on_delete=models.CASCADE)
    order = models.ForeignKey(Order, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
