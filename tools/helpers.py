from django.views.debug import SafeExceptionReporterFilter


class CustomExceptionFilter(SafeExceptionReporterFilter):
    def get_post_parameters(self, request):
        # Oculta POST
        return {}

    def get_get_parameters(self, request):
        # Oculta GET
        return {}

    def get_traceback_frame_variables(self, request, tb_frame):
        # Oculta variáveis locais dos frames
        return {}

    def get_request_headers(self, request):
        # Oculta headers
        return {}

    def get_cookies(self, request):
        # Oculta cookies
        return {}

    def get_file(self, request):
        # Oculta arquivos enviados
        return None

    def get_safe_settings(self):
        # Oculta todos os settings
        return {}
