from django.http import HttpResponse


class CorsMiddleware:
    """Permite que o front (HTML/JS aberto no navegador, Live Server etc.) chame esta API."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = HttpResponse(status=200) if request.method == "OPTIONS" else self.get_response(request)
        response["Access-Control-Allow-Origin"] = "*"
        response["Access-Control-Allow-Methods"] = "GET, POST, PUT, PATCH, DELETE, OPTIONS"
        response["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
        return response
