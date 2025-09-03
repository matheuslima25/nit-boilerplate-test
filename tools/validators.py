from django.conf import settings
from django.core.exceptions import ValidationError


class ModelSerializerValidator(object):
    def __init__(self):
        self.context = None
        self.instance = None

    def set_context(self, serializer):
        self.context = serializer.context
        self.instance = serializer.instance

    def __call__(self, value):
        operation = self.get_operation()  # type: ignore
        fn = getattr(self, 'validate_{}'.format(operation), None)
        if fn:
            fn(value)


def FileSizeValidator(image):
    file_size = image.size
    if file_size > settings.MAX_UPLOAD_SIZE:
        raise ValidationError(
            f"Max size of file is {settings.MAX_UPLOAD_SIZE / (1024 ** 2)} MB."
        )
