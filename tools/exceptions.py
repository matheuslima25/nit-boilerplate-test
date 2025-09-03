from requests.exceptions import HTTPError


class BadRequestError(HTTPError):
    """Erro 400: A requisição foi malformada ou inválida (sem retry)."""

    def __init__(self, response):
        self.response = response
        message = f"[HTTP 400] Requisição inválida: {response.text}"
        super().__init__(message, response=response)
