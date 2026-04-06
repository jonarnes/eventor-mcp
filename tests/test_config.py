import pytest
from pydantic import ValidationError

from eventor_mcp.config import Settings


def test_rejects_key_pasted_into_header_field() -> None:
    with pytest.raises(ValidationError, match="EVENTOR_API_KEY is empty"):
        Settings(
            _env_file=None,
            EVENTOR_API_KEY="",
            EVENTOR_API_KEY_HEADER="3a9a3b1cbfdf464e9872031c09203c76",
        )
