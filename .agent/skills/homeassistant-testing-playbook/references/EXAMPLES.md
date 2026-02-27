# Test Examples (Home Assistant)

Concrete snippets for common cases. Adapt names/paths to your integration.

## conftest.py core
```python
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.syrupy import HomeAssistantSnapshotExtension
from syrupy.assertion import SnapshotAssertion

from homeassistant.const import CONF_IP_ADDRESS

from custom_components.homewizard_instant.const import DOMAIN

@pytest.fixture
def mock_config_entry():
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="P1 Meter",
        data={CONF_IP_ADDRESS: "1.2.3.4"},
        unique_id=f"{DOMAIN}_HWE-P1_SERIAL123",
    )
    return entry

@pytest.fixture
def snapshot(snapshot: SnapshotAssertion) -> SnapshotAssertion:
    return snapshot.use_extension(HomeAssistantSnapshotExtension)

@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    yield
```

## test_config_flow.py (happy path + errors)
```python
from types import SimpleNamespace
from unittest.mock import patch

from homewizard_energy.const import Model
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.const import CONF_IP_ADDRESS

from custom_components.homewizard_instant.config_flow import RecoverableError
from custom_components.homewizard_instant.const import DOMAIN

async def test_user_flow_success(hass):
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": "user"})
    assert result["type"] == FlowResultType.FORM

    mock_device = SimpleNamespace(
        product_type=Model.P1_METER,
        product_name="P1 Meter",
        serial="SERIAL123",
    )
    with patch(
        "custom_components.homewizard_instant.config_flow.async_try_connect",
        return_value=mock_device,
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={CONF_IP_ADDRESS: "1.2.3.4"},
        )

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_IP_ADDRESS] == "1.2.3.4"

async def test_user_flow_network_error(hass):
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": "user"})
    with patch(
        "custom_components.homewizard_instant.config_flow.async_try_connect",
        side_effect=RecoverableError("boom", "network_error"),
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={CONF_IP_ADDRESS: "1.2.3.4"},
        )

    assert result["type"] == FlowResultType.FORM
    assert result["errors"] == {"base": "network_error"}
```

## test_init.py (setup/unload)
```python
from homeassistant.config_entries import ConfigEntryState
from pytest_homeassistant_custom_component.common import MockConfigEntry
from homeassistant.const import CONF_IP_ADDRESS
from unittest.mock import AsyncMock, patch

from custom_components.homewizard_instant.const import DOMAIN

async def test_setup_unload(hass):
    entry = MockConfigEntry(domain=DOMAIN, data={CONF_IP_ADDRESS: "1.2.3.4"})
    entry.add_to_hass(hass)

    with patch(
        "custom_components.homewizard_instant.HWEnergyDeviceUpdateCoordinator.async_config_entry_first_refresh",
        new=AsyncMock(return_value=None),
    ):
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    assert entry.state == ConfigEntryState.LOADED

    await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state == ConfigEntryState.NOT_LOADED
```

## test_sensor.py (coordinator + entity availability)
```python
from unittest.mock import AsyncMock

from custom_components.homewizard_instant.coordinator import HWEnergyDeviceUpdateCoordinator
from custom_components.homewizard_instant.sensor import HomeWizardSensorEntity, SENSORS

async def test_sensor_native_value_available(mock_config_entry, mock_combined_data, hass):
    coordinator = HWEnergyDeviceUpdateCoordinator(hass, mock_config_entry, api=AsyncMock())
    coordinator.data = mock_combined_data

    description = next(d for d in SENSORS if d.key == "active_power_w")
    entity = HomeWizardSensorEntity(coordinator, description)

    assert entity.native_value == 50.0
    assert entity.available is True
```

## Diagnostics snapshot
```python
from unittest.mock import patch

from custom_components.homewizard_instant.diagnostics import async_get_config_entry_diagnostics

async def test_diagnostics_snapshot(hass, mock_config_entry, snapshot):
    mock_config_entry.add_to_hass(hass)

    with patch(
        "custom_components.homewizard_instant.diagnostics.async_redact_data",
        side_effect=lambda value, _: value,
    ):
        diagnostics = await async_get_config_entry_diagnostics(hass, mock_config_entry)

    assert diagnostics == snapshot
```
