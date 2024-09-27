from django import template
from store.models import Cart

register = template.Library()

@register.simple_tag
def cart_item_count(user):
    if user.is_authenticated:
        try:
            cart = user.cart
            return cart.cartitem_set.count()
        except Cart.DoesNotExist:
            return 0
    return 0