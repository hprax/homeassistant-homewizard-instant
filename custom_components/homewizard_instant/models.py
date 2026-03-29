"""Data models for HomeWizard Energy v2 API."""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum
from typing import Any


class ExternalDeviceType(IntEnum):
    """Types of external devices connected to a P1 meter (DSMR MSn codes)."""

    GAS_METER = 3
    HEAT_METER = 5
    WARM_WATER_METER = 6
    WATER_METER = 7
    INLET_HEAT_METER = 8


@dataclass
class ExternalDevice:
    """An external device connected to the P1 meter."""

    unique_id: str
    type: ExternalDeviceType | None
    value: float | None
    unit: str | None
    timestamp: str | None


@dataclass
class DeviceV2:
    """Device information from HomeWizard v2 API (/api)."""

    product_name: str
    product_type: str
    serial: str
    firmware_version: str
    api_version: str

    @property
    def model_name(self) -> str:
        """Return the model name (same as product_name in v2)."""
        return self.product_name

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DeviceV2:
        """Create from API response dict."""
        return cls(
            product_name=data["product_name"],
            product_type=data["product_type"],
            serial=data["serial"],
            firmware_version=data["firmware_version"],
            api_version=data.get("api_version", "2.0.0"),
        )


@dataclass
class SystemV2:
    """System information from HomeWizard v2 API (/api/system)."""

    wifi_ssid: str | None = None
    wifi_rssi_db: int | None = None
    uptime_s: int | None = None
    cloud_enabled: bool | None = None
    status_led_brightness_pct: int | None = None
    api_v1_enabled: bool | None = None

    @property
    def wifi_strength_pct(self) -> float | None:
        """Convert Wi-Fi RSSI (dBm) to a 0–100% strength estimate."""
        if self.wifi_rssi_db is None:
            return None
        return max(0.0, min(100.0, float(self.wifi_rssi_db + 100)))

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SystemV2:
        """Create from API response dict."""
        return cls(
            wifi_ssid=data.get("wifi_ssid"),
            wifi_rssi_db=data.get("wifi_rssi_db"),
            uptime_s=data.get("uptime_s"),
            cloud_enabled=data.get("cloud_enabled"),
            status_led_brightness_pct=data.get("status_led_brightness_pct"),
            api_v1_enabled=data.get("api_v1_enabled"),
        )


@dataclass
class MeasurementV2:
    """Measurement data from HomeWizard v2 API (/api/measurement)."""

    # Meter metadata
    protocol_version: int | None = None
    meter_model: str | None = None
    unique_id: str | None = None
    tariff: int | None = None
    timestamp: str | None = None

    # Energy import (kWh)
    energy_import_kwh: float | None = None
    energy_import_t1_kwh: float | None = None
    energy_import_t2_kwh: float | None = None
    energy_import_t3_kwh: float | None = None
    energy_import_t4_kwh: float | None = None

    # Energy export (kWh)
    energy_export_kwh: float | None = None
    energy_export_t1_kwh: float | None = None
    energy_export_t2_kwh: float | None = None
    energy_export_t3_kwh: float | None = None
    energy_export_t4_kwh: float | None = None

    # Active power (W)
    power_w: float | None = None
    power_l1_w: float | None = None
    power_l2_w: float | None = None
    power_l3_w: float | None = None

    # Voltage (V)
    voltage_v: float | None = None
    voltage_l1_v: float | None = None
    voltage_l2_v: float | None = None
    voltage_l3_v: float | None = None

    # Current (A)
    current_a: float | None = None
    current_l1_a: float | None = None
    current_l2_a: float | None = None
    current_l3_a: float | None = None

    # Frequency (Hz)
    frequency_hz: float | None = None

    # Apparent power (VA)
    apparent_power_va: float | None = None
    apparent_power_l1_va: float | None = None
    apparent_power_l2_va: float | None = None
    apparent_power_l3_va: float | None = None

    # Reactive power (VAR)
    reactive_power_var: float | None = None
    reactive_power_l1_var: float | None = None
    reactive_power_l2_var: float | None = None
    reactive_power_l3_var: float | None = None

    # Power factor (0–1)
    power_factor: float | None = None
    power_factor_l1: float | None = None
    power_factor_l2: float | None = None
    power_factor_l3: float | None = None

    # Grid quality counters
    voltage_sag_l1_count: int | None = None
    voltage_sag_l2_count: int | None = None
    voltage_sag_l3_count: int | None = None
    voltage_swell_l1_count: int | None = None
    voltage_swell_l2_count: int | None = None
    voltage_swell_l3_count: int | None = None
    any_power_fail_count: int | None = None
    long_power_fail_count: int | None = None

    # Demand indicators
    average_power_15m_w: float | None = None
    monthly_power_peak_w: float | None = None
    monthly_power_peak_timestamp: str | None = None

    # External devices (gas, water, heat meters)
    external_devices: dict[str, ExternalDevice] | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> MeasurementV2:
        """Create from API/WebSocket response dict."""
        external_devices: dict[str, ExternalDevice] | None = None
        if external := data.get("external"):
            external_devices = {}
            for ext in external:
                unique_id = ext.get("unique_id", "")
                meter_type = ext.get("meter_type")
                try:
                    device_type: ExternalDeviceType | None = ExternalDeviceType(meter_type)
                except (ValueError, TypeError):
                    device_type = None
                external_devices[unique_id] = ExternalDevice(
                    unique_id=unique_id,
                    type=device_type,
                    value=ext.get("value"),
                    unit=ext.get("unit"),
                    timestamp=ext.get("timestamp"),
                )

        return cls(
            protocol_version=data.get("protocol_version"),
            meter_model=data.get("meter_model"),
            unique_id=data.get("unique_id"),
            tariff=data.get("tariff"),
            timestamp=data.get("timestamp"),
            energy_import_kwh=data.get("energy_import_kwh"),
            energy_import_t1_kwh=data.get("energy_import_t1_kwh"),
            energy_import_t2_kwh=data.get("energy_import_t2_kwh"),
            energy_import_t3_kwh=data.get("energy_import_t3_kwh"),
            energy_import_t4_kwh=data.get("energy_import_t4_kwh"),
            energy_export_kwh=data.get("energy_export_kwh"),
            energy_export_t1_kwh=data.get("energy_export_t1_kwh"),
            energy_export_t2_kwh=data.get("energy_export_t2_kwh"),
            energy_export_t3_kwh=data.get("energy_export_t3_kwh"),
            energy_export_t4_kwh=data.get("energy_export_t4_kwh"),
            power_w=data.get("power_w"),
            power_l1_w=data.get("power_l1_w"),
            power_l2_w=data.get("power_l2_w"),
            power_l3_w=data.get("power_l3_w"),
            voltage_v=data.get("voltage_v"),
            voltage_l1_v=data.get("voltage_l1_v"),
            voltage_l2_v=data.get("voltage_l2_v"),
            voltage_l3_v=data.get("voltage_l3_v"),
            current_a=data.get("current_a"),
            current_l1_a=data.get("current_l1_a"),
            current_l2_a=data.get("current_l2_a"),
            current_l3_a=data.get("current_l3_a"),
            frequency_hz=data.get("frequency_hz"),
            apparent_power_va=data.get("apparent_power_va"),
            apparent_power_l1_va=data.get("apparent_power_l1_va"),
            apparent_power_l2_va=data.get("apparent_power_l2_va"),
            apparent_power_l3_va=data.get("apparent_power_l3_va"),
            reactive_power_var=data.get("reactive_power_var"),
            reactive_power_l1_var=data.get("reactive_power_l1_var"),
            reactive_power_l2_var=data.get("reactive_power_l2_var"),
            reactive_power_l3_var=data.get("reactive_power_l3_var"),
            power_factor=data.get("power_factor"),
            power_factor_l1=data.get("power_factor_l1"),
            power_factor_l2=data.get("power_factor_l2"),
            power_factor_l3=data.get("power_factor_l3"),
            voltage_sag_l1_count=data.get("voltage_sag_l1_count"),
            voltage_sag_l2_count=data.get("voltage_sag_l2_count"),
            voltage_sag_l3_count=data.get("voltage_sag_l3_count"),
            voltage_swell_l1_count=data.get("voltage_swell_l1_count"),
            voltage_swell_l2_count=data.get("voltage_swell_l2_count"),
            voltage_swell_l3_count=data.get("voltage_swell_l3_count"),
            any_power_fail_count=data.get("any_power_fail_count"),
            long_power_fail_count=data.get("long_power_fail_count"),
            average_power_15m_w=data.get("average_power_15m_w"),
            monthly_power_peak_w=data.get("monthly_power_peak_w"),
            monthly_power_peak_timestamp=data.get("monthly_power_peak_timestamp"),
            external_devices=external_devices,
        )


@dataclass
class DeviceResponseV2:
    """Combined device data passed to sensors via the coordinator."""

    device: DeviceV2
    measurement: MeasurementV2
    system: SystemV2 | None = None
