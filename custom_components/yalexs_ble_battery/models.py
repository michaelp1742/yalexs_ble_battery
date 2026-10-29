"""The Yale Access Bluetooth Battery integration models."""

from dataclasses import dataclass

from yalexs_ble import PushLock


@dataclass
class YaleXSBLEBatteryData:
    """Data for the battery entry of one lock."""

    address: str
    lock: PushLock
    read_activity_log: bool
