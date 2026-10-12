from .services import items
def cart_context(request):
    return {"cart_count":sum(items(request.session).values())}
