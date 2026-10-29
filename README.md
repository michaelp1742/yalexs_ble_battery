# Yale Access Bluetooth Battery

A custom integration for Home Assistant that shows the battery voltage a Yale lock writes into its activity log.
It works beside Home Assistant's [Yale Access Bluetooth](https://www.home-assistant.io/integrations/yalexs_ble/)
integration and uses that integration's connection to the lock.

It is a proof of concept of a parallel integration: it adds to a lock that Yale Access Bluetooth has loaded, and it
changes nothing in Yale Access Bluetooth itself.

## Requirements

- Home Assistant 2026.10.0 or later.
- The Yale Access Bluetooth integration, set up for the lock.
- yalexs-ble from [Yale-Libs/yalexs-ble#426](https://github.com/Yale-Libs/yalexs-ble/pull/426) on, or a release
  that contains it. The yalexs-ble that Home Assistant 2026.10 installs, 4.0.1, has neither
  `register_log_record_callback` nor `parse_log_event_packet`, and this integration needs both.

## Installation

Copy `custom_components/yalexs_ble_battery` into the `custom_components` folder of your Home Assistant
configuration, then restart Home Assistant.

## Setup

1. In **Settings** > **Devices & services**, add **Yale Access Bluetooth Battery**.
2. Pick the lock. The list shows each lock that Yale Access Bluetooth has loaded and that has no battery entry yet.

The entry starts with its option off. It then adds no entity and reads nothing from the lock.

## The activity log option

In the entry's options, turn on **Read the activity log for the battery voltage**.

Home Assistant reads each record off the lock. A record it reads never reaches the Yale Home or August app's activity
feed or the cloud.

With the option on, the entry adds the sensor **Battery voltage (activity log)**. The sensor is on a device of the
entry's own, which has the same Bluetooth connection as the Yale Access Bluetooth device for the lock. Once the
option is turned off, the entry reads nothing from the lock. The sensor stays, shown as unavailable, and keeps its
history.

## The sensor

- The sensor shows the battery voltage in the last `LockOperation` record that Home Assistant has read from the
  lock, in volts to the millivolt.
- Its `time_stamp` attribute is the record's time from the lock's clock, in seconds since 1970 UTC.
- It updates each time Home Assistant reads a `LockOperation` record from the lock, and no other record changes it.
  In testing on a lock with a keypad and a card reader, each of 28 accepted PIN, fingerprint, or card entries wrote a
  record of another type. A `LockOperation` record followed each within a minute, and in 26 of the 28 it held the
  same voltage as the entry's record. On such a lock the sensor updates at that `LockOperation` record, such as the
  record of the relock that follows.
- It keeps its last reading across restarts of Home Assistant.
- It shows the value the lock writes, with no range check.

## Development

```sh
uv venv --python 3.14
uv pip install -r requirements_test.txt
.venv/bin/python -m pytest
.venv/bin/pre-commit run --all-files
```
