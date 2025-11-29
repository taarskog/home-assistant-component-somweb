"""Common fixtures for the SOMweb tests."""

from collections.abc import Generator
from unittest.mock import AsyncMock, MagicMock, patch
import sys

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.syrupy import HomeAssistantSnapshotExtension
from syrupy.assertion import SnapshotAssertion

from homeassistant.const import (
    CONF_ID,
    CONF_MODE,
    CONF_PASSWORD,
    CONF_URL,
    CONF_USERNAME,
)

# Mock the somweb module before importing our integration
sys.modules["somweb"] = MagicMock()
from custom_components.somweb.const import DOMAIN, MODE_CLOUD, MODE_LOCAL  # noqa: E402


@pytest.fixture
def snapshot(snapshot: SnapshotAssertion) -> SnapshotAssertion:
    """Return snapshot assertion fixture with the Home Assistant extension."""
    return snapshot.use_extension(HomeAssistantSnapshotExtension)


@pytest.fixture(autouse=True)
async def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable custom integrations for all tests."""
    return


@pytest.fixture
def mock_somweb_client():
    """Return a mocked SomwebClient."""
    with patch(
        "custom_components.somweb.config_flow.SomwebClient"
    ) as mock_client_class:
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_client_class.create_using_udi.return_value = mock_client

        # Configure mock behavior
        mock_client.async_is_alive = AsyncMock(return_value=True)
        mock_client.async_authenticate = AsyncMock(return_value=MagicMock(success=True))
        mock_client.async_get_udi = AsyncMock(return_value="TEST-UDI-123")
        mock_client.udi = "TEST-UDI-123"
        mock_client.close = AsyncMock()

        yield mock_client_class


@pytest.fixture
def mock_setup_entry() -> Generator[AsyncMock]:
    """Override async_setup_entry."""
    with patch(
        "custom_components.somweb.async_setup_entry",
        return_value=True,
    ) as mock_setup_entry:
        yield mock_setup_entry


@pytest.fixture
def mock_config_entry_local() -> MockConfigEntry:
    """Return a mock config entry for local mode."""
    return MockConfigEntry(
        domain=DOMAIN,
        title="SOMweb TEST-UDI-123",
        data={
            CONF_MODE: MODE_LOCAL,
            CONF_ID: "TEST-UDI-123",
            CONF_URL: "http://192.168.1.100",
            CONF_USERNAME: "testuser",
            CONF_PASSWORD: "testpass",
        },
        unique_id="TEST-UDI-123",
        version=1,
        minor_version=2,
    )


@pytest.fixture
def mock_config_entry_cloud() -> MockConfigEntry:
    """Return a mock config entry for cloud mode."""
    return MockConfigEntry(
        domain=DOMAIN,
        title="SOMweb TEST-UDI-123",
        data={
            CONF_MODE: MODE_CLOUD,
            CONF_ID: "TEST-UDI-123",
            CONF_URL: None,
            CONF_USERNAME: "testuser",
            CONF_PASSWORD: "testpass",
        },
        unique_id="TEST-UDI-123",
        version=1,
        minor_version=2,
    )
