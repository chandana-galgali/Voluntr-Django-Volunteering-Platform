"""Email backend that sends through Brevo's HTTPS API instead of SMTP.

Render's free web services block outbound SMTP ports (25/465/587), so an SMTP
configuration that works locally silently fails in production. Brevo's
transactional API runs over HTTPS (port 443) and is not affected.
Enable it by setting BREVO_API_KEY in the environment.
"""
import json
import logging
import urllib.error
import urllib.request
from email.utils import parseaddr

from django.conf import settings
from django.core.mail.backends.base import BaseEmailBackend

log = logging.getLogger(__name__)
API_URL = 'https://api.brevo.com/v3/smtp/email'


def _address(value):
    name, email = parseaddr(value or '')
    data = {'email': email}
    if name:
        data['name'] = name
    return data


class BrevoEmailBackend(BaseEmailBackend):
    def __init__(self, fail_silently=False, api_key=None, timeout=None, **kwargs):
        super().__init__(fail_silently=fail_silently, **kwargs)
        self.api_key = api_key or getattr(settings, 'BREVO_API_KEY', '')
        self.timeout = timeout or getattr(settings, 'EMAIL_TIMEOUT', 10) or 10

    def _payload(self, message):
        payload = {
            'sender': _address(message.from_email or settings.DEFAULT_FROM_EMAIL),
            'to': [_address(a) for a in message.to],
            'subject': message.subject,
            'textContent': message.body or ' ',
        }
        if message.cc:
            payload['cc'] = [_address(a) for a in message.cc]
        if message.bcc:
            payload['bcc'] = [_address(a) for a in message.bcc]
        if message.reply_to:
            payload['replyTo'] = _address(message.reply_to[0])
        for content, mimetype in getattr(message, 'alternatives', []) or []:
            if mimetype == 'text/html':
                payload['htmlContent'] = content
        return payload

    def send_messages(self, email_messages):
        if not email_messages:
            return 0
        if not self.api_key:
            if not self.fail_silently:
                raise RuntimeError('BREVO_API_KEY is not configured.')
            return 0
        sent = 0
        for message in email_messages:
            if not message.recipients():
                continue
            request = urllib.request.Request(
                API_URL,
                data=json.dumps(self._payload(message)).encode('utf-8'),
                headers={'api-key': self.api_key, 'Content-Type': 'application/json', 'Accept': 'application/json'},
                method='POST',
            )
            try:
                with urllib.request.urlopen(request, timeout=self.timeout) as response:
                    if 200 <= response.status < 300:
                        sent += 1
            except urllib.error.HTTPError as exc:
                detail = exc.read().decode('utf-8', 'replace')[:500]
                log.error('Brevo rejected email (%s): %s', exc.code, detail)
                if not self.fail_silently:
                    raise
            except Exception:
                log.exception('Brevo email request failed')
                if not self.fail_silently:
                    raise
        return sent
