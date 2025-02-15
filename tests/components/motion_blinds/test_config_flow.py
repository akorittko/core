"""Test the Motion Blinds config flow."""
import socket
from unittest.mock import Mock, patch

import pytest

from homeassistant import config_entries, data_entry_flow
from homeassistant.components import dhcp
from homeassistant.components.motion_blinds import const
from homeassistant.components.motion_blinds.config_flow import DEFAULT_GATEWAY_NAME
from homeassistant.const import CONF_API_KEY, CONF_HOST

from tests.common import MockConfigEntry

TEST_HOST = "1.2.3.4"
TEST_HOST2 = "5.6.7.8"
TEST_HOST_HA = "9.10.11.12"
TEST_HOST_ANY = "any"
TEST_API_KEY = "12ab345c-d67e-8f"
TEST_API_KEY2 = "f8e76dc5-43ba-21"
TEST_MAC = "ab:cd:ef:gh"
TEST_MAC2 = "ij:kl:mn:op"
TEST_DEVICE_LIST = {TEST_MAC: Mock()}

TEST_DISCOVERY_1 = {
    TEST_HOST: {
        "msgType": "GetDeviceListAck",
        "mac": TEST_MAC,
        "deviceType": "02000002",
        "ProtocolVersion": "0.9",
        "token": "12345A678B9CDEFG",
        "data": [
            {"mac": "abcdefghujkl", "deviceType": "02000002"},
            {"mac": "abcdefghujkl0001", "deviceType": "10000000"},
            {"mac": "abcdefghujkl0002", "deviceType": "10000000"},
        ],
    }
}

TEST_DISCOVERY_2 = {
    TEST_HOST: {
        "msgType": "GetDeviceListAck",
        "mac": TEST_MAC,
        "deviceType": "02000002",
        "ProtocolVersion": "0.9",
        "token": "12345A678B9CDEFG",
        "data": [
            {"mac": "abcdefghujkl", "deviceType": "02000002"},
            {"mac": "abcdefghujkl0001", "deviceType": "10000000"},
        ],
    },
    TEST_HOST2: {
        "msgType": "GetDeviceListAck",
        "mac": TEST_MAC2,
        "deviceType": "02000002",
        "ProtocolVersion": "0.9",
        "token": "12345A678B9CDEFG",
        "data": [
            {"mac": "abcdefghujkl", "deviceType": "02000002"},
            {"mac": "abcdefghujkl0001", "deviceType": "10000000"},
        ],
    },
}

TEST_INTERFACES = [
    {"enabled": True, "default": True, "ipv4": [{"address": TEST_HOST_HA}]}
]


@pytest.fixture(name="motion_blinds_connect", autouse=True)
def motion_blinds_connect_fixture(mock_get_source_ip):
    """Mock motion blinds connection and entry setup."""
    with patch(
        "homeassistant.components.motion_blinds.gateway.MotionGateway.GetDeviceList",
        return_value=True,
    ), patch(
        "homeassistant.components.motion_blinds.gateway.MotionGateway.Update",
        return_value=True,
    ), patch(
        "homeassistant.components.motion_blinds.gateway.MotionGateway.device_list",
        TEST_DEVICE_LIST,
    ), patch(
        "homeassistant.components.motion_blinds.gateway.MotionGateway.mac",
        TEST_MAC,
    ), patch(
        "homeassistant.components.motion_blinds.config_flow.MotionDiscovery.discover",
        return_value=TEST_DISCOVERY_1,
    ), patch(
        "homeassistant.components.motion_blinds.config_flow.AsyncMotionMulticast.Start_listen",
        return_value=True,
    ), patch(
        "homeassistant.components.motion_blinds.config_flow.AsyncMotionMulticast.Stop_listen",
        return_value=True,
    ), patch(
        "homeassistant.components.motion_blinds.config_flow.network.async_get_adapters",
        return_value=TEST_INTERFACES,
    ), patch(
        "homeassistant.components.motion_blinds.async_setup_entry", return_value=True
    ):
        yield


async def test_config_flow_manual_host_success(hass):
    """Successful flow manually initialized by the user."""
    result = await hass.config_entries.flow.async_init(
        const.DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    assert result["type"] == "form"
    assert result["step_id"] == "user"
    assert result["errors"] == {}

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_HOST: TEST_HOST},
    )

    assert result["type"] == "form"
    assert result["step_id"] == "connect"
    assert result["errors"] == {}

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_API_KEY: TEST_API_KEY},
    )

    assert result["type"] == "create_entry"
    assert result["title"] == DEFAULT_GATEWAY_NAME
    assert result["data"] == {
        CONF_HOST: TEST_HOST,
        CONF_API_KEY: TEST_API_KEY,
        const.CONF_INTERFACE: TEST_HOST_HA,
    }


async def test_config_flow_discovery_1_success(hass):
    """Successful flow with 1 gateway discovered."""
    result = await hass.config_entries.flow.async_init(
        const.DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    assert result["type"] == "form"
    assert result["step_id"] == "user"
    assert result["errors"] == {}

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {},
    )

    assert result["type"] == "form"
    assert result["step_id"] == "connect"
    assert result["errors"] == {}

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_API_KEY: TEST_API_KEY},
    )

    assert result["type"] == "create_entry"
    assert result["title"] == DEFAULT_GATEWAY_NAME
    assert result["data"] == {
        CONF_HOST: TEST_HOST,
        CONF_API_KEY: TEST_API_KEY,
        const.CONF_INTERFACE: TEST_HOST_HA,
    }


async def test_config_flow_discovery_2_success(hass):
    """Successful flow with 2 gateway discovered."""
    result = await hass.config_entries.flow.async_init(
        const.DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    assert result["type"] == "form"
    assert result["step_id"] == "user"
    assert result["errors"] == {}

    with patch(
        "homeassistant.components.motion_blinds.config_flow.MotionDiscovery.discover",
        return_value=TEST_DISCOVERY_2,
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {},
        )

    assert result["type"] == "form"
    assert result["step_id"] == "select"
    assert result["data_schema"].schema["select_ip"].container == [
        TEST_HOST,
        TEST_HOST2,
    ]
    assert result["errors"] is None

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {"select_ip": TEST_HOST2},
    )

    assert result["type"] == "form"
    assert result["step_id"] == "connect"
    assert result["errors"] == {}

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_API_KEY: TEST_API_KEY},
    )

    assert result["type"] == "create_entry"
    assert result["title"] == DEFAULT_GATEWAY_NAME
    assert result["data"] == {
        CONF_HOST: TEST_HOST2,
        CONF_API_KEY: TEST_API_KEY,
        const.CONF_INTERFACE: TEST_HOST_HA,
    }


async def test_config_flow_connection_error(hass):
    """Failed flow manually initialized by the user with connection timeout."""
    result = await hass.config_entries.flow.async_init(
        const.DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    assert result["type"] == "form"
    assert result["step_id"] == "user"
    assert result["errors"] == {}

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_HOST: TEST_HOST},
    )

    assert result["type"] == "form"
    assert result["step_id"] == "connect"
    assert result["errors"] == {}

    with patch(
        "homeassistant.components.motion_blinds.gateway.MotionGateway.GetDeviceList",
        side_effect=socket.timeout,
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_API_KEY: TEST_API_KEY},
        )

    assert result["type"] == "abort"
    assert result["reason"] == "connection_error"


async def test_config_flow_discovery_fail(hass):
    """Failed flow with no gateways discovered."""
    result = await hass.config_entries.flow.async_init(
        const.DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    assert result["type"] == "form"
    assert result["step_id"] == "user"
    assert result["errors"] == {}

    with patch(
        "homeassistant.components.motion_blinds.config_flow.MotionDiscovery.discover",
        return_value={},
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {},
        )

    assert result["type"] == "form"
    assert result["step_id"] == "user"
    assert result["errors"] == {"base": "discovery_error"}


async def test_config_flow_interface(hass):
    """Successful flow manually initialized by the user with interface specified."""
    result = await hass.config_entries.flow.async_init(
        const.DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    assert result["type"] == "form"
    assert result["step_id"] == "user"
    assert result["errors"] == {}

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_HOST: TEST_HOST},
    )

    assert result["type"] == "form"
    assert result["step_id"] == "connect"
    assert result["errors"] == {}

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_API_KEY: TEST_API_KEY, const.CONF_INTERFACE: TEST_HOST_HA},
    )

    assert result["type"] == "create_entry"
    assert result["title"] == DEFAULT_GATEWAY_NAME
    assert result["data"] == {
        CONF_HOST: TEST_HOST,
        CONF_API_KEY: TEST_API_KEY,
        const.CONF_INTERFACE: TEST_HOST_HA,
    }


async def test_config_flow_invalid_interface(hass):
    """Failed flow manually initialized by the user with invalid interface."""
    result = await hass.config_entries.flow.async_init(
        const.DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    assert result["type"] == "form"
    assert result["step_id"] == "user"
    assert result["errors"] == {}

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_HOST: TEST_HOST},
    )

    assert result["type"] == "form"
    assert result["step_id"] == "connect"
    assert result["errors"] == {}

    with patch(
        "homeassistant.components.motion_blinds.config_flow.AsyncMotionMulticast.Start_listen",
        side_effect=socket.gaierror,
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_API_KEY: TEST_API_KEY, const.CONF_INTERFACE: TEST_HOST_HA},
        )

    assert result["type"] == "form"
    assert result["step_id"] == "connect"
    assert result["errors"] == {const.CONF_INTERFACE: "invalid_interface"}


async def test_dhcp_flow(hass):
    """Successful flow from DHCP discovery."""
    dhcp_data = dhcp.DhcpServiceInfo(
        ip=TEST_HOST,
        hostname="MOTION_abcdef",
        macaddress=TEST_MAC,
    )

    result = await hass.config_entries.flow.async_init(
        const.DOMAIN, context={"source": config_entries.SOURCE_DHCP}, data=dhcp_data
    )

    assert result["type"] == "form"
    assert result["step_id"] == "connect"
    assert result["errors"] == {}

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_API_KEY: TEST_API_KEY},
    )

    assert result["type"] == "create_entry"
    assert result["title"] == DEFAULT_GATEWAY_NAME
    assert result["data"] == {
        CONF_HOST: TEST_HOST,
        CONF_API_KEY: TEST_API_KEY,
        const.CONF_INTERFACE: TEST_HOST_HA,
    }


async def test_options_flow(hass):
    """Test specifying non default settings using options flow."""
    config_entry = MockConfigEntry(
        domain=const.DOMAIN,
        unique_id=TEST_MAC,
        data={
            CONF_HOST: TEST_HOST,
            CONF_API_KEY: TEST_API_KEY,
        },
        title=DEFAULT_GATEWAY_NAME,
    )
    config_entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    result = await hass.config_entries.options.async_init(config_entry.entry_id)

    assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
    assert result["step_id"] == "init"

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={const.CONF_WAIT_FOR_PUSH: False},
    )

    assert result["type"] == data_entry_flow.RESULT_TYPE_CREATE_ENTRY
    assert config_entry.options == {
        const.CONF_WAIT_FOR_PUSH: False,
    }


async def test_change_connection_settings(hass):
    """Test changing connection settings by issuing a second user config flow."""
    config_entry = MockConfigEntry(
        domain=const.DOMAIN,
        unique_id=TEST_MAC,
        data={
            CONF_HOST: TEST_HOST,
            CONF_API_KEY: TEST_API_KEY,
            const.CONF_INTERFACE: TEST_HOST_HA,
        },
        title=DEFAULT_GATEWAY_NAME,
    )
    config_entry.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        const.DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    assert result["type"] == "form"
    assert result["step_id"] == "user"
    assert result["errors"] == {}

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_HOST: TEST_HOST2},
    )

    assert result["type"] == "form"
    assert result["step_id"] == "connect"
    assert result["errors"] == {}

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_API_KEY: TEST_API_KEY2, const.CONF_INTERFACE: TEST_HOST_ANY},
    )

    assert result["type"] == "abort"
    assert config_entry.data[CONF_HOST] == TEST_HOST2
    assert config_entry.data[CONF_API_KEY] == TEST_API_KEY2
    assert config_entry.data[const.CONF_INTERFACE] == TEST_HOST_ANY
