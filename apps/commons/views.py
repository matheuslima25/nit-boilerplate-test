import requests
from django.conf import settings
from django.http import HttpResponseRedirect, JsonResponse
from django.views.decorators.http import require_http_methods


def index(request):
    if request.method == "GET":
        return HttpResponseRedirect(settings.HONEYPOT_URL)


@require_http_methods(["GET"])
def keycloak_status(request):
    """
    Endpoint on-demand para verificar status do Keycloak.
    GET /status/keycloak/
    """
    try:
        url = f"{settings.KEYCLOAK_SERVER_URL}/admin"
        response = requests.get(url, timeout=5, allow_redirects=False)
        
        if response.status_code in [200, 302]:
            return JsonResponse({
                "service": "keycloak",
                "status": "healthy",
                "url": url,
                "response_code": response.status_code
            })
        else:
            return JsonResponse({
                "service": "keycloak", 
                "status": "unhealthy",
                "error": f"HTTP {response.status_code}",
                "url": url
            }, status=503)
            
    except requests.exceptions.RequestException as e:
        return JsonResponse({
            "service": "keycloak",
            "status": "unhealthy", 
            "error": str(e),
            "url": getattr(settings, 'KEYCLOAK_SERVER_URL', 'not configured')
        }, status=503)


@require_http_methods(["GET"])
def kong_status(request):
    """
    Endpoint on-demand para verificar status do Kong.
    GET /status/kong/
    """
    try:
        url = f"{settings.KONG_ADMIN_URL}/status"
        response = requests.get(url, timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            return JsonResponse({
                "service": "kong",
                "status": "healthy",
                "url": url,
                "server_info": data.get("server", {})
            })
        else:
            return JsonResponse({
                "service": "kong",
                "status": "unhealthy", 
                "error": f"HTTP {response.status_code}",
                "url": url
            }, status=503)
            
    except requests.exceptions.RequestException as e:
        return JsonResponse({
            "service": "kong",
            "status": "unhealthy",
            "error": str(e), 
            "url": getattr(settings, 'KONG_ADMIN_URL', 'not configured')
        }, status=503)


@require_http_methods(["GET"])
def system_status(request):
    """
    Endpoint agregado para verificar status de todos os serviços.
    GET /status/
    """
    # Verificar Keycloak
    keycloak_healthy = False
    keycloak_error = None
    try:
        url = f"{settings.KEYCLOAK_SERVER_URL}/admin"
        response = requests.get(url, timeout=5, allow_redirects=False)
        keycloak_healthy = response.status_code in [200, 302]
    except Exception as e:
        keycloak_error = str(e)
    
    # Verificar Kong
    kong_healthy = False
    kong_error = None
    try:
        url = f"{settings.KONG_ADMIN_URL}/status"
        response = requests.get(url, timeout=5)
        kong_healthy = response.status_code == 200
    except Exception as e:
        kong_error = str(e)
    
    # Status geral
    overall_healthy = keycloak_healthy and kong_healthy
    
    status_data = {
        "overall_status": "healthy" if overall_healthy else "degraded",
        "services": {
            "keycloak": {
                "status": "healthy" if keycloak_healthy else "unhealthy",
                "error": keycloak_error
            },
            "kong": {
                "status": "healthy" if kong_healthy else "unhealthy", 
                "error": kong_error
            }
        },
        "timestamp": request.META.get('HTTP_DATE', 'unknown')
    }
    
    return JsonResponse(
        status_data,
        status=200 if overall_healthy else 503
    )
