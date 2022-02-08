from enum import IntEnum


class OperatingState(IntEnum):
    INIT_MEMORY = 0
    INIT_VERSION_DISPLAY = 1
    INIT_BATTERY_DISPLAY = 2
    MASTER_OFF = 3
    SLEEP = 4
    IDLE = 5
    TEMP_SELECT = 6  # pressing device button for profile switch
    HEAT_CYCLE_PREHEAT = 7
    HEAT_CYCLE_ACTIVE = 8
    HEAT_CYCLE_FADE = 9
    VERSION_DISPLAY = 10
    BATTERY_DISPLAY = 11
    FACTORY_TEST = 12  # unknown
    BONDING = 13  # BLE pairing


class DeviceCommands(IntEnum):
    MASTER_OFF = 0
    SLEEP = 1
    IDLE = 2
    TEMP_SELECT_BEGIN = 3
    TEMP_SELECT_STOP = 4
    SHOW_BATTERY_LEVEL = 5
    SHOW_VERSION = 6
    HEAT_CYCLE_START = 7
    HEAT_CYCLE_ABORT = 8
    HEAT_CYCLE_BOOST = 9
    FACTORY_TEST = 10
    BONDING = 11


class ChamberType(IntEnum):
    NONE = 0
    CLASSIC = 1
    HERBAL = 2  # ?? possibly a future chamber?
    PERFORMANCE = 3


PeakProModels = {
    '0': 'Peak Pro',
    '1': 'Opal Peak Pro',
    '2': 'Indiglow Peak Pro',
    '21': 'Peak Pro',
    '22': 'Opal Peak Pro',
    '4294967295': 'Peak Pro'
}

PROFILE_TO_BYTE_ARRAY = {0: bytearray([0, 0, 0, 0]),
                         1: bytearray([0, 0, 128, 63]),
                         2: bytearray([0, 0, 0, 64]),
                         3: bytearray([0, 0, 64, 64])}


class LanternAnimation:
    # first byte *may* be brightness level (0-255)
    DISCO_MODE = b'\xff \x08\x01\x00\x00\x00\x00'
    ROTATING = b'\xff\xff\x00\x00\x15\x00\x00\x00'
    PULSING = b'\xff\xff\x00\x00\x05\x00\x00\x00'
    all = [PULSING, ROTATING, DISCO_MODE]  # same order as LanternSettings.animation_toggles


class Constants:
    DABBING_ADDED_TEMP_FAHRENHEIT = 10
    DABBING_ADDED_TEMP_CELSIUS = 5
    DABBING_ADDED_TIME = 10
    TEMPERATURE_MAX_FAHRENHEIT = 620
    TEMPERATURE_MIN_FAHRENHEIT = 400
    LANTERN_TIME_SEC = 7200
    BOOST_TEMPERATURE_MIN_FAHRENHEIT = 0
    BOOST_TEMPERATURE_MAX_FAHRENHEIT = 36
    BOOST_TEMPERATURE_MIN_CELSIUS = 0
    BOOST_TEMPERATURE_MAX_CELSIUS = 20
    BOOST_DURATION_MIN = 0
    BOOST_DURATION_MAX = 60
    DEFAULT_BOOST_TEMP_FAHRENHEIT = 10
    DEFAULT_BOOST_TEMP_CELSIUS = 5
    DEFAULT_BOOST_DURATION = 15
    FACTORY_HEX_COLORS = {'low': '#0000ff',
                          'medium': '#6ee916',
                          'high': '#f80b00',
                          'peak': '#ffffff'}
    BRIGHTNESS_MIN = 0
    BRIGHTNESS_MAX = 255


class PuffcoCharacteristics:
    MANUFACTURER = "{00002a29-0000-1000-8000-00805f9b34fb}"
    MODEL = "{00002a24-0000-1000-8000-00805f9b34fb}"
    SERIAL = "{00002a25-0000-1000-8000-00805f9b34fb}"
    HW_REV = "{00002a27-0000-1000-8000-00805f9b34fb}"
    SW_REV = "{00002a28-0000-1000-8000-00805f9b34fb}"

    BATTERY_SOC = "{f9a98c15-c651-4f34-b656-d100bf580020}"
    BATTERY_CHARGE_STATE = "{f9a98c15-c651-4f34-b656-d100bf580031}"
    BATTERY_CHARGE_FULL_ETA = "{f9a98c15-c651-4f34-b656-d100bf580033}"

    UUID = "{06caf9c0-74d3-454f-9be9-e30cd999c17a}"  # used to discover Peak Pro devices w/o needing MAC address
    BIRTHDAY = "{f9a98c15-c651-4f34-b656-d100bf58004e}"

    LANTERN_STATUS = "{f9a98c15-c651-4f34-b656-d100bf58004a}"
    LANTERN_BRIGHTNESS = "{f9a98c15-c651-4f34-b656-d100bf58004b}"
    LANTERN_COLOR = "{f9a98c15-c651-4f34-b656-d100bf580048}"

    BOOST_TEMP = "{f9a98c15-c651-4f34-b656-d100bf580067}"
    BOOST_TIME = "{f9a98c15-c651-4f34-b656-d100bf580068}"
    BOOST_TEMP_OVERRIDE = "{f9a98c15-c651-4f34-b656-d100bf580045}"
    BOOST_TIME_OVERRIDE = "{f9a98c15-c651-4f34-b656-d100bf580046}"

    OPERATING_STATE = "{f9a98c15-c651-4f34-b656-d100bf580022}"
    STATE_ELAPSED_TIME = "{f9a98c15-c651-4f34-b656-d100bf580023}"
    STATE_TOTAL_TIME = "{f9a98c15-c651-4f34-b656-d100bf580024}"
    HEATER_TEMP = "{f9a98c15-c651-4f34-b656-d100bf580025}"
    HEATER_TARGET_TEMP = "{f9a98c15-c651-4f34-b656-d100bf580026}"

    COMMAND = "{f9a98c15-c651-4f34-b656-d100bf580040}"
    TOTAL_DAB_COUNT = "{f9a98c15-c651-4f34-b656-d100bf58002f}"
    DABS_PER_DAY = "{f9a98c15-c651-4f34-b656-d100bf58003b}"
    DEVICE_NAME = "{f9a98c15-c651-4f34-b656-d100bf58004d}"

    PROFILE_CURRENT = "{f9a98c15-c651-4f34-b656-d100bf580041}"
    STEALTH_STATUS = "{f9a98c15-c651-4f34-b656-d100bf580042}"
    PROFILE = "{f9a98c15-c651-4f34-b656-d100bf580061}"
    PROFILE_NAME = "{f9a98c15-c651-4f34-b656-d100bf580062}"
    PROFILE_PREHEAT_TEMP = "{f9a98c15-c651-4f34-b656-d100bf580063}"
    PROFILE_PREHEAT_TIME = "{f9a98c15-c651-4f34-b656-d100bf580064}"
    PROFILE_COLOR = "{f9a98c15-c651-4f34-b656-d100bf580065}"
