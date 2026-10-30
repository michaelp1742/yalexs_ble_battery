# Yale Access Bluetooth Battery

A proof of concept of a parallel integration for Home Assistant. It adds a battery voltage sensor to a Yale lock that
Home Assistant's [Yale Access Bluetooth](https://www.home-assistant.io/integrations/yalexs_ble/) integration has
loaded. It uses that integration's connection to the lock and changes nothing in Yale Access Bluetooth itself.

The voltage comes from the lock's activity log. The integration reads the log through the changes of
[Yale-Libs/yalexs-ble#422](https://github.com/Yale-Libs/yalexs-ble/pull/422) to
[#426](https://github.com/Yale-Libs/yalexs-ble/pull/426), which hand every record the library reads to each
registered reader as the 18 bytes the lock sent, with a decoder for them.

## What it shows

A parallel integration has a domain of its own. It finds the lock's `PushLock` on Yale Access Bluetooth's loaded
config entry and adds its feature there. A feature that is policy over what the library already does therefore needs
no change to Yale Access Bluetooth and no Home Assistant release. A new mechanism in the library still needs a
library release and a bump of Home Assistant's pin, which is why this integration needs a yalexs-ble built from #426.

This integration is a first case. It registers one reader of the activity log, decodes each record with
`parse_log_event_packet`, and publishes the lock's battery voltage from the records that hold it.

## The activity log changes it is built on

The lock keeps a log of what happens to it, one record for each event, such as a lock operation, a keypad or
credential entry, or a door change. The records written for a lock operation, a valid keypad entry, a credential
entry, and a credential added or deleted hold the lock's battery voltage in millivolts. A `GetLog` command returns the
oldest unread record, so a client reads the log one record at a time, oldest first. On the locks tested, a record that
one client has read is gone for every other, the vendor's app and cloud included.

These five pull requests change how yalexs-ble reads the log. Each is stacked on the one before it, so a build from
#426 has them all.

| Pull request | What it adds |
|---|---|
| [#422](https://github.com/Yale-Libs/yalexs-ble/pull/422) | the cause of a lock operation, from the record's `opCode`, in place of `UNKNOWN` or `PIN` |
| [#423](https://github.com/Yale-Libs/yalexs-ble/pull/423) | `Lock.get_log`, which sends one `GetLog` and returns the reply unparsed, and a `LockStatus` member for each of the six lock states it lacked |
| [#424](https://github.com/Yale-Libs/yalexs-ble/pull/424) | `parse_log_event_packet`, which decodes an 18-byte `GetLog` reply into a Python record, in Yale's numbering or August's |
| [#425](https://github.com/Yale-Libs/yalexs-ble/pull/425) | `register_log_record_callback`: every record reaches each reader as the 18 bytes the lock sent, with a `backlog` flag |
| [#426](https://github.com/Yale-Libs/yalexs-ble/pull/426) | the drain in a task of its own, started on each new connection and each settled lock or door change |

The library sends each `GetLog` once and hands the reply to every registered reader in turn, awaiting each before the
next read. This integration is one such reader: it calls `parse_log_event_packet` on each record and publishes the
voltage from the records that hold it. Other integrations can register readers on the same `PushLock` beside it, and
one drain serves them all.

## Requirements

- Home Assistant 2026.10.0 or later.
- The Yale Access Bluetooth integration, set up for the lock.
- yalexs-ble from [Yale-Libs/yalexs-ble#426](https://github.com/Yale-Libs/yalexs-ble/pull/426) on, or a release
  that contains it. The yalexs-ble that Home Assistant 2026.10 installs, 4.0.1, has neither
  `register_log_record_callback` nor `parse_log_event_packet`, and this integration needs both.
- At each start, Home Assistant installs the yalexs-ble version that Yale Access Bluetooth pins, in place of any
  other. Another version stays installed when Home Assistant runs with `--skip-pip-packages yalexs-ble`, or with
  `--skip-pip`, which skips the requirements of every integration.
- yalexs-ble from #426 requires cryptography 50.0.2 or later, and Home Assistant 2026.10 pins cryptography 50.0.1,
  so no cryptography version meets both.
- With yalexs-ble 4.0.1 in place, the entry fails to set up while its activity log option is on, and Home Assistant
  logs an `ImportError`.

## Installation

Copy `custom_components/yalexs_ble_battery` into the `custom_components` folder of your Home Assistant
configuration, then restart Home Assistant.

## Setup

1. In **Settings** > **Devices & services**, add **Yale Access Bluetooth Battery**.
2. Pick the lock. The list shows each lock that Yale Access Bluetooth has loaded and that has no battery entry yet.

The entry starts with its option off. It then adds no entity and reads nothing from the lock.

## The activity log option

In the entry's options, turn on **Read the activity log for the battery voltage**.

Home Assistant reads records directly off the lock. These records never reach the cloud for Activity reporting. The
battery levels in the app also stop updating.

With the option on, the entry adds the sensor **Battery voltage (activity log)**. The sensor is on a device of the
entry's own, which has the same Bluetooth connection as the Yale Access Bluetooth device for the lock. Once the
option is turned off, the entry reads nothing from the lock. The sensor stays, shown as unavailable, and keeps its
history.

## The sensor

- The sensor shows the lock's battery voltage, in volts to the millivolt, from the last record that Home Assistant
  has read from the lock for one of these events:
  - a lock operation;
  - a valid PIN or fingerprint entry at the keypad;
  - a credential entry, such as an RF card;
  - a credential added or deleted.
- Its `time_stamp` attribute is the record's time from the lock's clock, in seconds since 1970 UTC.
- It updates each time Home Assistant reads one of those records, and no other record changes it. The record of the
  keypad's own battery never changes it. On an August lock, the record types that only August numbers, `0x14` to
  `0x1E`, never change it.
- It keeps its last reading across restarts of Home Assistant.
- It shows the value the lock writes, with no range check.

## Icon

The integration's icon is drawn from the battery Bluetooth variant icon (`mdi-battery-bluetooth-variant`) of Material
Design Icons by [Pictogrammers](https://pictogrammers.com/), which is under the Apache License 2.0.

## Development

```sh
uv venv --python 3.14
uv pip install -r requirements_test.txt
.venv/bin/python -m pytest
.venv/bin/pre-commit run --all-files
```
