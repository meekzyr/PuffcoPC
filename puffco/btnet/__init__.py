import struct
from base64 import b64decode
from enum import IntEnum


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


class ChamberType(IntEnum):
    NONE = 0
    CLASSIC = 1
    HERBAL = 2  # ?? possibly a future chamber?
    PERFORMANCE = 3


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


PeakProModels = {
    '0': 'Peak Pro',
    '1': 'Opal Peak Pro',
    '2': 'Indiglow Peak Pro',
    '21': 'Peak Pro',
    '22': 'Opal Peak Pro',
    '25': 'Guardian Peak Pro',
    '26': 'Guardian Peak Pro',
    '4': 'Guardian Peak Pro',
    '4294967295': 'Peak Pro',
    '12': 'Peach White Peak Pro',  # same as peach desert
    '13': 'Peach Black Peak Pro',  # same as peach desert
    '51': 'Peak Pro',
    '71': 'Peach Black Peak Pro',  # same as peach desert
    '72': 'Peach White Peak Pro',  # same as peach desert
    '15': 'Peach Desert Peak Pro',
    '74': 'Peach Desert Peak Pro',
}


class Characteristics:
    SERVICE_UUID = "06caf9c0-74d3-454f-9be9-e30cd999c17a"  # used to discover Peak Pro devices w/o needing MAC address

    MANUFACTURER_NAME = "00002a29-0000-1000-8000-00805f9b34fb"
    MODEL_NUMBER = "00002a24-0000-1000-8000-00805f9b34fb"
    SERIAL_NUMBER = "00002a25-0000-1000-8000-00805f9b34fb"
    HARDWARE_REVISION = "00002a27-0000-1000-8000-00805f9b34fb"
    SOFTWARE_REVISION = "00002a28-0000-1000-8000-00805f9b34fb"
    SOFTWARE_REV_GIT_HASH = "F9A98C15-C651-4F34-B656-D100BF580002"
    ACCESS_SEED_KEY = 'F9A98C15-C651-4F34-B656-D100BF5800E0'

    MODE_COMMAND = "F9A98C15-C651-4F34-B656-D100BF580040"
    HEATER_TEMP = "F9A98C15-C651-4F34-B656-D100BF580025"
    HEATER_TARGET_TEMP = "F9A98C15-C651-4F34-B656-D100BF580026"
    DEVICE_NAME = "F9A98C15-C651-4F34-B656-D100BF58004D"
    OPERATING_STATE = "F9A98C15-C651-4F34-B656-D100BF580022"
    STATE_ELAPSED_TIME = "F9A98C15-C651-4F34-B656-D100BF580023"
    STATE_TOTAL_TIME = "F9A98C15-C651-4F34-B656-D100BF580024"

    LANTERN_STATUS = "F9A98C15-C651-4F34-B656-D100BF58004A"
    LANTERN_COLOR = "F9A98C15-C651-4F34-B656-D100BF580048"
    LANTERN_BRIGHTNESS = "F9A98C15-C651-4F34-B656-D100BF58004B"
    DABS_PER_DAY = "F9A98C15-C651-4F34-B656-D100BF58003B"
    TOTAL_DAB_COUNT = "F9A98C15-C651-4F34-B656-D100BF58002F"
    STEALTH_STATUS = "F9A98C15-C651-4F34-B656-D100BF580042"
    DEVICE_BIRTHDAY = "F9A98C15-C651-4F34-B656-D100BF58004E"

    PROFILE_CURRENT = "F9A98C15-C651-4F34-B656-D100BF580041"
    PROFILE = "F9A98C15-C651-4F34-B656-D100BF580061"
    PROFILE_NAME = "F9A98C15-C651-4F34-B656-D100BF580062"
    PROFILE_PREHEAT_TEMP = "F9A98C15-C651-4F34-B656-D100BF580063"
    PROFILE_PREHEAT_TIME = "F9A98C15-C651-4F34-B656-D100BF580064"
    PROFILE_COLOR = "F9A98C15-C651-4F34-B656-D100BF580065"

    BATTERY_SOC = "F9A98C15-C651-4F34-B656-D100BF580020"
    BATTERY_CHARGE_STATE = "F9A98C15-C651-4F34-B656-D100BF580031"
    BATTERY_CHARGE_FULL_ETA = "F9A98C15-C651-4F34-B656-D100BF580033"

    BOOST_TEMP = "F9A98C15-C651-4F34-B656-D100BF580067"
    BOOST_TIME = "F9A98C15-C651-4F34-B656-D100BF580068"
    TEMPERATURE_OVERRIDE = "F9A98C15-C651-4F34-B656-D100BF580045"
    TIME_OVERRIDE = "F9A98C15-C651-4F34-B656-D100BF580046"


class LoraxCharacteristics:
    LORAX_SERVICE_UUID = 'e276967f-ea8a-478a-a92e-d78f5dd15dd5'
    LORAX_VERSION = '05434bca-cc7f-4ef6-bbb3-b1c520b9800c'
    LORAX_COMMAND = '60133d5c-5727-4f2c-9697-d842c5292a3c'
    LORAX_REPLY = '8dc5ec05-8f7d-45ad-99db-3fbde65dbd9c'
    LORAX_EVENT = '43312cd1-7d34-46ce-a7d3-0a98fd9b4cb8'
    PROTOCOL_CHARS = [LORAX_VERSION, LORAX_COMMAND, LORAX_REPLY, LORAX_EVENT]

    MODEL_NUMBER = "/p/sys/hw/mdcd"
    SERIAL_NUMBER = "/p/sys/hw/ser"
    HARDWARE_REVISION = "/p/sys/hw/ver"
    SOFTWARE_REVISION = "/p/sys/fw/ver"
    SOFTWARE_REV_GIT_HASH = "/p/sys/fw/gith"

    MODE_COMMAND = "/p/app/mc"
    HEATER_TEMP = "/p/app/htr/temp"
    HEATER_TARGET_TEMP = "/p/app/htr/tcmd"
    DEVICE_NAME = "/u/sys/name"
    READY_MODE_CYCLE_SELECT = "/u/app/rdym/hc"
    OPERATING_STATE = "/p/app/stat/id"
    STATE_ELAPSED_TIME = "/p/app/stat/elap"
    STATE_TOTAL_TIME = "/p/app/stat/tott"

    LANTERN_STATUS = "/p/app/ltrn/cmd"
    LANTERN_COLOR = "/p/app/ltrn/colr"
    LANTERN_BRIGHTNESS = "/u/app/ui/lbrt"
    DABS_PER_DAY = "/p/app/info/dpd"
    TOTAL_DAB_COUNT = "/p/app/odom/0/nc"
    STEALTH_STATUS = "/u/app/ui/stlm"
    DEVICE_BIRTHDAY = "/u/sys/bday"

    PROFILE_CURRENT = "/p/app/hcs"
    PROFILE_NAME = "/u/app/hc/%N/name"
    PROFILE_PREHEAT_TEMP = "/u/app/hc/%N/temp"
    PROFILE_PREHEAT_TIME = "/u/app/hc/%N/time"
    PROFILE_COLOR = "/u/app/hc/%N/colr"

    BATTERY_SOC = "/p/bat/soc"
    BATTERY_CHARGE_STATE = "/p/bat/chg/stat"
    BATTERY_CHARGE_FULL_ETA = "/p/bat/chg/etf"

    BOOST_TEMP = "/u/app/hc/%N/btmp"
    BOOST_TIME = "/u/app/hc/%N/btim"
    TEMPERATURE_OVERRIDE = "/p/app/tmpo"
    TIME_OVERRIDE = "/p/app/timo"


CHAR_UUID2LORAX_PATH = {getattr(Characteristics, k): v for (k, v) in LoraxCharacteristics.__dict__.items()
                        if (k.isupper() and isinstance(v, str)) and hasattr(Characteristics, k)}


class LoraxOpCodes:
    GET_ACCESS_SEED = 0
    UNLOCK_ACCESS = 1
    GET_LIMITS = 2
    READ_SHORT = 16
    WRITE_SHORT = 17

    WRITE = 34  # for buffers


DEVICE_HANDSHAKE_KEY = bytearray(b64decode('FUrZc0WilhUBteT2JlCc+A=='))
DEVICE_HANDSHAKE2_KEY = bytearray(b64decode('ZMZFYlbyb1scoSc3pd1x+w=='))


def parse(data, fmt='f'):
    _struct = struct.unpack(fmt, data)
    remove = ['(', ',', ')']
    for chars in remove:
        _struct = str(_struct).replace(chars, "")
    return _struct
