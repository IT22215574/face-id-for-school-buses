from types import SimpleNamespace
from unittest.mock import patch, MagicMock

import pytest
from fastapi import HTTPException
from app.services.tracking_auth import create_tracking_token
from app.api.routes.auth import firebase_token


def test_tracking_disabled_by_default():
    with patch('app.services.tracking_auth.get_settings', return_value=SimpleNamespace(FIREBASE_TRACKING_ENABLED=False)):
        with pytest.raises(HTTPException) as error:
            create_tracking_token(7)
    assert error.value.status_code == 503


def test_bridge_uses_verified_account_id():
    with patch('app.services.tracking_auth.create_tracking_token', return_value='signed') as mint:
        assert firebase_token(SimpleNamespace(id=7)) == {'token': 'signed'}
    mint.assert_called_once_with(7)


def test_custom_token_uid_and_no_credentials_exposed():
    fake = MagicMock()
    fake.auth.create_custom_token.return_value = b'signed-token'
    settings = SimpleNamespace(FIREBASE_TRACKING_ENABLED=True)
    with patch('app.services.tracking_auth.get_settings', return_value=settings), patch.dict('sys.modules', {'firebase_admin': fake}):
        assert create_tracking_token(7) == 'signed-token'
        fake.auth.create_custom_token.assert_called_once_with('account_7', app=fake.get_app.return_value)
        fake.auth.create_custom_token.side_effect = ValueError('private credential details')
        with pytest.raises(HTTPException) as error:
            create_tracking_token(7)
        assert error.value.status_code == 503
        assert 'private' not in error.value.detail
