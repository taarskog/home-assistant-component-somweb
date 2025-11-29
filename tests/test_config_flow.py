"""Test the SOMweb config flow."""

from unittest.mock import AsyncMock, MagicMock

from homeassistant import config_entries
from homeassistant.const import (
    CONF_BASE,
    CONF_ID,
    CONF_MODE,
    CONF_PASSWORD,
    CONF_URL,
    CONF_USERNAME,
)
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers.service_info.zeroconf import ZeroconfServiceInfo
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.somweb.const import DOMAIN, MODE_CLOUD, MODE_LOCAL

# Test data
TEST_UDI = "TEST-UDI-123"
TEST_URL = "http://192.168.1.100"
TEST_USERNAME = "testuser"
TEST_PASSWORD = "testpass"


async def test_user_form_local(
    hass: HomeAssistant,
    mock_somweb_client,
    mock_setup_entry: AsyncMock,
) -> None:
    """Test the user config flow for local mode - happy path."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_USER},
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result.get("errors") is None or result.get("errors") == {}

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_MODE: MODE_LOCAL,
            CONF_URL: TEST_URL,
            CONF_USERNAME: TEST_USERNAME,
            CONF_PASSWORD: TEST_PASSWORD,
        },
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == f"SOMweb {TEST_UDI}"
    assert result["data"] == {
        CONF_MODE: MODE_LOCAL,
        CONF_ID: TEST_UDI,
        CONF_URL: TEST_URL,
        CONF_USERNAME: TEST_USERNAME,
        CONF_PASSWORD: TEST_PASSWORD,
    }
    assert len(mock_setup_entry.mock_calls) == 1


async def test_user_form_cloud(
    hass: HomeAssistant,
    mock_somweb_client,
    mock_setup_entry: AsyncMock,
) -> None:
    """Test the user config flow for cloud mode - happy path."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_USER},
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_MODE: MODE_CLOUD,
            CONF_ID: TEST_UDI,
            CONF_USERNAME: TEST_USERNAME,
            CONF_PASSWORD: TEST_PASSWORD,
        },
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == f"SOMweb {TEST_UDI}"
    assert result["data"] == {
        CONF_MODE: MODE_CLOUD,
        CONF_ID: TEST_UDI,
        CONF_URL: None,  # URL should be None for cloud mode
        CONF_USERNAME: TEST_USERNAME,
        CONF_PASSWORD: TEST_PASSWORD,
    }
    assert len(mock_setup_entry.mock_calls) == 1


async def test_user_form_local_missing_url(
    hass: HomeAssistant,
    mock_somweb_client,
) -> None:
    """Test error when URL is missing in local mode."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_USER},
    )

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_MODE: MODE_LOCAL,
            CONF_URL: "",  # Empty URL
            CONF_USERNAME: TEST_USERNAME,
            CONF_PASSWORD: TEST_PASSWORD,
        },
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {CONF_URL: "invalid_url"}


async def test_user_form_cloud_missing_udi(
    hass: HomeAssistant,
    mock_somweb_client,
) -> None:
    """Test error when UDI is missing in cloud mode."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_USER},
    )

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_MODE: MODE_CLOUD,
            CONF_ID: "",  # Empty UDI
            CONF_USERNAME: TEST_USERNAME,
            CONF_PASSWORD: TEST_PASSWORD,
        },
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {CONF_ID: "invalid_udi"}


async def test_user_form_cannot_connect(
    hass: HomeAssistant,
    mock_somweb_client,
) -> None:
    """Test connection error during user flow."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_USER},
    )

    # Configure mock to fail connection
    mock_somweb_client.return_value.async_is_alive = AsyncMock(return_value=False)

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_MODE: MODE_LOCAL,
            CONF_URL: TEST_URL,
            CONF_USERNAME: TEST_USERNAME,
            CONF_PASSWORD: TEST_PASSWORD,
        },
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {CONF_BASE: "cannot_connect"}


async def test_user_form_invalid_auth(
    hass: HomeAssistant,
    mock_somweb_client,
) -> None:
    """Test invalid authentication during user flow."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_USER},
    )

    # Configure mock to fail authentication
    mock_somweb_client.return_value.async_authenticate = AsyncMock(
        return_value=MagicMock(success=False)
    )

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_MODE: MODE_LOCAL,
            CONF_URL: TEST_URL,
            CONF_USERNAME: TEST_USERNAME,
            CONF_PASSWORD: TEST_PASSWORD,
        },
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {CONF_BASE: "invalid_auth"}


async def test_user_form_unknown_exception(
    hass: HomeAssistant,
    mock_somweb_client,
) -> None:
    """Test handling of unexpected exception during user flow."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_USER},
    )

    # Configure mock to raise exception
    mock_somweb_client.return_value.async_is_alive = AsyncMock(
        side_effect=Exception("Unexpected error")
    )

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_MODE: MODE_LOCAL,
            CONF_URL: TEST_URL,
            CONF_USERNAME: TEST_USERNAME,
            CONF_PASSWORD: TEST_PASSWORD,
        },
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {CONF_BASE: "unknown"}


async def test_user_form_already_configured(
    hass: HomeAssistant,
    mock_somweb_client,
    mock_config_entry_local: MockConfigEntry,
) -> None:
    """Test aborting if device is already configured."""
    mock_config_entry_local.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_USER},
    )

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_MODE: MODE_LOCAL,
            CONF_URL: TEST_URL,
            CONF_USERNAME: TEST_USERNAME,
            CONF_PASSWORD: TEST_PASSWORD,
        },
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_zeroconf_discovery(
    hass: HomeAssistant,
    mock_somweb_client,
) -> None:
    """Test zeroconf discovery flow."""
    discovery_info = ZeroconfServiceInfo(
        ip_address="192.168.1.100",
        ip_addresses=["192.168.1.100"],
        hostname="somweb.local.",
        name="somweb._hap._tcp.local.",
        port=80,
        type="_hap._tcp.local.",
        properties={},
    )

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_ZEROCONF},
        data=discovery_info,
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "discovery_confirm"
    assert result["description_placeholders"] == {
        "url": "http://192.168.1.100",
        "udi": TEST_UDI,
    }


async def test_zeroconf_discovery_not_somweb(
    hass: HomeAssistant,
) -> None:
    """Test zeroconf discovery aborts for non-SOMweb devices."""
    discovery_info = ZeroconfServiceInfo(
        ip_address="192.168.1.100",
        ip_addresses=["192.168.1.100"],
        hostname="other-device.local.",
        name="other._hap._tcp.local.",
        port=80,
        type="_hap._tcp.local.",
        properties={},
    )

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_ZEROCONF},
        data=discovery_info,
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "not_somweb_device"


async def test_zeroconf_discovery_already_configured(
    hass: HomeAssistant,
    mock_somweb_client,
    mock_config_entry_local: MockConfigEntry,
) -> None:
    """Test zeroconf discovery aborts if device already configured."""
    mock_config_entry_local.add_to_hass(hass)

    discovery_info = ZeroconfServiceInfo(
        ip_address="192.168.1.100",
        ip_addresses=["192.168.1.100"],
        hostname="somweb.local.",
        name="somweb._hap._tcp.local.",
        port=80,
        type="_hap._tcp.local.",
        properties={},
    )

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_ZEROCONF},
        data=discovery_info,
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_zeroconf_discovery_cannot_connect(
    hass: HomeAssistant,
    mock_somweb_client,
) -> None:
    """Test zeroconf discovery aborts if cannot connect."""
    # Configure mock to fail connection
    mock_somweb_client.return_value.async_is_alive = AsyncMock(return_value=False)

    discovery_info = ZeroconfServiceInfo(
        ip_address="192.168.1.100",
        ip_addresses=["192.168.1.100"],
        hostname="somweb.local.",
        name="somweb._hap._tcp.local.",
        port=80,
        type="_hap._tcp.local.",
        properties={},
    )

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_ZEROCONF},
        data=discovery_info,
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "cannot_connect"


async def test_discovery_confirm(
    hass: HomeAssistant,
    mock_somweb_client,
    mock_setup_entry: AsyncMock,
) -> None:
    """Test discovery confirmation flow."""
    discovery_info = ZeroconfServiceInfo(
        ip_address="192.168.1.100",
        ip_addresses=["192.168.1.100"],
        hostname="somweb.local.",
        name="somweb._hap._tcp.local.",
        port=80,
        type="_hap._tcp.local.",
        properties={},
    )

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_ZEROCONF},
        data=discovery_info,
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "discovery_confirm"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_USERNAME: TEST_USERNAME,
            CONF_PASSWORD: TEST_PASSWORD,
        },
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == f"SOMweb {TEST_UDI}"
    assert result["data"] == {
        CONF_MODE: MODE_LOCAL,
        CONF_ID: TEST_UDI,
        CONF_URL: "http://192.168.1.100",
        CONF_USERNAME: TEST_USERNAME,
        CONF_PASSWORD: TEST_PASSWORD,
    }
    assert len(mock_setup_entry.mock_calls) == 1


async def test_discovery_confirm_invalid_auth(
    hass: HomeAssistant,
    mock_somweb_client,
) -> None:
    """Test discovery confirmation with invalid authentication."""
    discovery_info = ZeroconfServiceInfo(
        ip_address="192.168.1.100",
        ip_addresses=["192.168.1.100"],
        hostname="somweb.local.",
        name="somweb._hap._tcp.local.",
        port=80,
        type="_hap._tcp.local.",
        properties={},
    )

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_ZEROCONF},
        data=discovery_info,
    )

    # Configure mock to fail authentication
    mock_somweb_client.return_value.async_authenticate = AsyncMock(
        return_value=MagicMock(success=False)
    )

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_USERNAME: TEST_USERNAME,
            CONF_PASSWORD: TEST_PASSWORD,
        },
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {CONF_BASE: "invalid_auth"}


async def test_discovery_confirm_cannot_connect(
    hass: HomeAssistant,
    mock_somweb_client,
) -> None:
    """Test discovery confirmation with connection error."""
    discovery_info = ZeroconfServiceInfo(
        ip_address="192.168.1.100",
        ip_addresses=["192.168.1.100"],
        hostname="somweb.local.",
        name="somweb._hap._tcp.local.",
        port=80,
        type="_hap._tcp.local.",
        properties={},
    )

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_ZEROCONF},
        data=discovery_info,
    )

    # Configure mock to fail connection during confirmation
    mock_somweb_client.return_value.async_is_alive = AsyncMock(return_value=False)

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_USERNAME: TEST_USERNAME,
            CONF_PASSWORD: TEST_PASSWORD,
        },
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {CONF_BASE: "cannot_connect"}


async def test_reconfigure_local(
    hass: HomeAssistant,
    mock_somweb_client,
    mock_config_entry_local: MockConfigEntry,
) -> None:
    """Test reconfigure flow for local mode."""
    mock_config_entry_local.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={
            "source": config_entries.SOURCE_RECONFIGURE,
            "entry_id": mock_config_entry_local.entry_id,
        },
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "reconfigure"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_MODE: MODE_LOCAL,
            CONF_URL: "http://192.168.1.200",  # Changed URL
            CONF_USERNAME: "newuser",  # Changed username
            CONF_PASSWORD: "newpass",  # Changed password
        },
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"
    assert dict(mock_config_entry_local.data) == {
        CONF_MODE: MODE_LOCAL,
        CONF_ID: TEST_UDI,
        CONF_URL: "http://192.168.1.200",
        CONF_USERNAME: "newuser",
        CONF_PASSWORD: "newpass",
    }


async def test_reconfigure_cloud(
    hass: HomeAssistant,
    mock_somweb_client,
    mock_config_entry_cloud: MockConfigEntry,
) -> None:
    """Test reconfigure flow for cloud mode."""
    mock_config_entry_cloud.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={
            "source": config_entries.SOURCE_RECONFIGURE,
            "entry_id": mock_config_entry_cloud.entry_id,
        },
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "reconfigure"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_MODE: MODE_CLOUD,
            CONF_ID: TEST_UDI,
            CONF_USERNAME: "newuser",  # Changed username
            CONF_PASSWORD: "newpass",  # Changed password
        },
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"
    assert dict(mock_config_entry_cloud.data) == {
        CONF_MODE: MODE_CLOUD,
        CONF_ID: TEST_UDI,
        CONF_URL: None,  # Should remain None for cloud mode
        CONF_USERNAME: "newuser",
        CONF_PASSWORD: "newpass",
    }


async def test_reconfigure_invalid_auth(
    hass: HomeAssistant,
    mock_somweb_client,
    mock_config_entry_local: MockConfigEntry,
) -> None:
    """Test reconfigure with invalid authentication."""
    mock_config_entry_local.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={
            "source": config_entries.SOURCE_RECONFIGURE,
            "entry_id": mock_config_entry_local.entry_id,
        },
    )

    # Configure mock to fail authentication
    mock_somweb_client.return_value.async_authenticate = AsyncMock(
        return_value=MagicMock(success=False)
    )

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_MODE: MODE_LOCAL,
            CONF_URL: TEST_URL,
            CONF_USERNAME: TEST_USERNAME,
            CONF_PASSWORD: "wrongpass",
        },
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {CONF_BASE: "invalid_auth"}


async def test_reconfigure_cannot_connect(
    hass: HomeAssistant,
    mock_somweb_client,
    mock_config_entry_local: MockConfigEntry,
) -> None:
    """Test reconfigure with connection error."""
    mock_config_entry_local.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={
            "source": config_entries.SOURCE_RECONFIGURE,
            "entry_id": mock_config_entry_local.entry_id,
        },
    )

    # Configure mock to fail connection
    mock_somweb_client.return_value.async_is_alive = AsyncMock(return_value=False)

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_MODE: MODE_LOCAL,
            CONF_URL: TEST_URL,
            CONF_USERNAME: TEST_USERNAME,
            CONF_PASSWORD: TEST_PASSWORD,
        },
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {CONF_BASE: "cannot_connect"}
