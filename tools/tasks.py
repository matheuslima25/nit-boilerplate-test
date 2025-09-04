import traceback

import six  # type: ignore
from django.conf import settings
from django.core.mail import EmailMultiAlternatives, mail_admins
from django.template import Context, Template
from django.template.loader import get_template, select_template


class Tasks:
    def send_email_task(
        self,
        subject="",
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=None,
        bcc=None,
        params=None,
        template="",
        mimetype="text/html; charset=UTF-8",
        headers=None,
    ):
        if headers is None:
            headers = {}
        if params is None:
            params = {}
        if bcc is None:
            bcc = []
        if to is None:
            to = []
        try:
            assert subject is not None
            assert from_email is not None
            assert to is not None
            assert bcc is not None
            assert params is not None
            assert template is not None
            assert mimetype is not None
            assert headers is not None

            try:
                if isinstance(template, six.string_types):
                    template_content = get_template(template)
                else:
                    template_content = select_template(template)
                html_content = template_content.render(params)
            except Exception:
                template_content = Template(template)
                html_content = template_content.render(Context(params))

            text_content = subject
            msg = EmailMultiAlternatives(
                subject, text_content, from_email, to, bcc=bcc, headers=headers
            )
            msg.attach_alternative(html_content, mimetype)
            msg.send()

        except Exception as exc:
            error_subject = "send_email_task failure"
            error_message = "%s\n%s" % (traceback.format_exc(), locals())
            mail_admins(error_subject, error_message)
            raise exc
        return "Email enviado com sucesso!"
