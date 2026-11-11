class SensitivePagesMiddleware:
    def __init__(self,get_response):
        self.get_response=get_response
    def __call__(self,request):
        response=self.get_response(request)
        if request.path.startswith(("/cuenta/","/carrito/","/checkout/","/mis-pedidos/","/dashboard/","/pagos/","/admin/")):
            response["Cache-Control"]="private, no-store, max-age=0"
        return response


class AppModeMiddleware:
    """Presentation only: the APK identifies itself; never grants permissions."""
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        from django.utils.cache import patch_vary_headers
        native = "CarrancoApp/" in request.META.get("HTTP_USER_AGENT", "")
        preview = request.COOKIES.get("carranco_app_preview") == "1"
        choice = request.GET.get("modo")
        if choice in ("app", "web"):
            preview = choice == "app"
        request.app_mode = (native or preview) and not request.path.startswith(("/admin/", "/dashboard/"))
        response = self.get_response(request)
        patch_vary_headers(response, ("Cookie", "User-Agent"))
        if choice == "app":
            response.set_cookie("carranco_app_preview", "1", max_age=86400, httponly=True,
                                secure=request.is_secure(), samesite="Lax")
        elif choice == "web":
            response.delete_cookie("carranco_app_preview", samesite="Lax")
        return response
