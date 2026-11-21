from django.shortcuts import redirect
from django.utils.cache import patch_vary_headers


class SensitivePagesMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if request.path.startswith(("/cuenta/", "/carrito/", "/checkout/", "/mis-pedidos/", "/dashboard/", "/pagos/", "/admin/")):
            response["Cache-Control"] = "private, no-store, max-age=0"
        return response


class AppModeMiddleware:
    """Presentation is per request. Neither a cookie nor a session enables APK mode."""
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        native = "CarrancoApp/" in request.META.get("HTTP_USER_AGENT", "")
        choice = request.GET.get("modo")
        requested = choice == "app" or (native and choice != "web")
        staff = request.user.is_authenticated and request.user.is_active and request.user.is_staff
        request.app_mode = requested and not staff and not request.path.startswith(("/admin/", "/dashboard/"))
        if staff and requested and request.method == "GET" and request.path in ("/", "/cuenta/", "/cuenta/login/", "/cuenta/registro/"):
            response = redirect("dashboard:inicio")
        else:
            response = self.get_response(request)
        patch_vary_headers(response, ("Cookie", "User-Agent"))
        if "carranco_app_preview" in request.COOKIES:
            response.delete_cookie("carranco_app_preview", samesite="Lax")
        if choice in ("app", "web") or staff:
            response["Cache-Control"] = "private, no-store, max-age=0"
        return response
