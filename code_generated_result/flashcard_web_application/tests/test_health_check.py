import pytest
from unittest.mock import patch
from fastapi import Request, HTTPException, Depends
from backend.main import health_check


@pytest.mark.asyncio
async def test_health_check_success():
    # source_info: backend.main.health_check
    result = await health_check()
    assert result == {"status": "ok"}