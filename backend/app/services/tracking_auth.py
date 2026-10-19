import json
import logging

from fastapi import HTTPException
from app.core.config import get_settings


def create_tracking_token(account_id: int) -> str:
    settings = get_settings()
    if not settings.FIREBASE_TRACKING_ENABLED:
        raise HTTPException(503, 'Firebase tracking is not configured')
    try:
        import firebase_admin
        from firebase_admin import auth, credentials
        try:
            app = firebase_admin.get_app('tracking')
        except ValueError:
            app = firebase_admin.initialize_app(
                credentials.Certificate(json.loads(settings.FCM_CREDENTIALS_JSON)),
                {'projectId': settings.FCM_PROJECT_ID}, name='tracking')
        token = auth.create_custom_token(f'account_{account_id}', app=app)
        return token.decode() if isinstance(token, bytes) else token
    except Exception:
        logging.getLogger(__name__).exception('Firebase token creation failed')
        raise HTTPException(503, 'Location authentication is temporarily unavailable') from None
