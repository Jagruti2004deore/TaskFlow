
from datetime import datetime, timedelta, timezone

import jwt
import pytest

from security import (
    ALGORITHM,
    SECRET_KEY,
    create_access_token,
    decode_access_token,
)


def test_create_and_decode_access_token():
    token = create_access_token(user_id=123)

    payload = decode_access_token(token)

    assert payload["sub"] == "123"
    assert "exp" in payload


def test_invalid_token_is_rejected():
    with pytest.raises(jwt.InvalidTokenError):
        decode_access_token("this-is-not-a-valid-token")


def test_expired_token_is_rejected():
    expired_payload = {
        "sub": "123",
        "exp": datetime.now(timezone.utc) - timedelta(minutes=1),
    }

    expired_token = jwt.encode(
        expired_payload,
        SECRET_KEY,
        algorithm=ALGORITHM,
    )

    with pytest.raises(jwt.ExpiredSignatureError):
        decode_access_token(expired_token)

