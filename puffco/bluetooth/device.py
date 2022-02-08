import struct
import typing
from datetime import datetime
from asyncio import wrap_future

from PyQt5.QtBluetooth import QLowEnergyService, QLowEnergyCharacteristic
from PyQt5.QtCore import QByteArray, QObject, pyqtSignal

from . import parse, thread_operation
from .characteristic import CharacteristicInfo
from .constants import *
from .objects import Worker, ReadFuture


class PeakPro(QObject):
    connected = False
    ready = pyqtSignal()

    def __init__(self, device, controller):
        QObject.__init__(self)
        self.device = self.qtd = device
        self.controller = controller
        self.controller.found_services.connect(self.device_services_retrieved)
        self.controller.disconnected.connect(self.on_disconnect)

        self.__callbacks = {}
        self.__write_callbacks = {}
        self.characteristics = {}
        self.services = []

        self.pending_fetch = []
        self.received = []

        self.LANTERN_ENABLED = None
        self.LANTERN_COLOR = None

    def on_disconnect(self, *args):
        """ Called when a BLE device is disconnected """
        self.connected = False

    @property
    def is_connected(self):
        return self.connected is True

    def get_cached_char_data(self, uuid):
        return self.characteristics[uuid].value

    async def async_write_characteristic(self, uuid, value: typing.Union[QByteArray, bytearray, bytes]) -> None:
        uuid = uuid.lower()
        assert uuid in self.characteristics, f'Unknown characteristic: {uuid}'

        fut = ReadFuture()
        char = self.characteristics[uuid]
        self.__write_callbacks.setdefault(uuid, []).append(fut)
        char.service.writeCharacteristic(char.characteristic, value,
                                         mode=QLowEnergyService.WriteMode.WriteWithResponse)
        result = await wrap_future(fut)
        return result.data()

    def write_characteristic(self, uuid: str, value: typing.Union[QByteArray, bytearray, bytes]) -> None:
        uuid = uuid.lower()
        assert uuid in self.characteristics, f'Unknown characteristic: {uuid}'
        char = self.characteristics[uuid]
        return char.service.writeCharacteristic(char.characteristic, value,
                                                mode=QLowEnergyService.WriteMode.WriteWithResponse)

    async def read_characteristic(self, _uuid) -> None:
        uuid = _uuid.lower()
        if uuid not in self.characteristics:
            return None

        fut = ReadFuture()
        char = self.characteristics[uuid]
        self.__callbacks.setdefault(uuid, []).append(fut)
        char.service.readCharacteristic(char.characteristic)
        result = await wrap_future(fut)
        return result.data()

    def wrote_characteristic(self, new_characteristic: "QLowEnergyCharacteristic", val: "QByteArray"):
        """
        Callback from QT BLE.
        The characteristic object's value is correctly set, we just need to map it to our dict.
        """
        assert new_characteristic.value() == val, 'Characteristic value does not match bytearray'
        char_uuid = new_characteristic.uuid().toString()
        assert char_uuid in self.characteristics, f'Received QT callback for unknown characteristic: {char_uuid}'
        callbacks = self.__write_callbacks.get(char_uuid, [])
        for callback in callbacks:
            self.__write_callbacks[char_uuid].remove(callback)
            callback(val)

        self.characteristics[char_uuid].set_characteristic(new_characteristic)

    def device_service_recv_details(self, state):
        if state != QLowEnergyService.ServiceState.ServiceDiscovered:
            return

        service: QLowEnergyService = self.sender()
        service.characteristicRead.connect(self._read_characteristic)
        service.characteristicWritten.connect(self.wrote_characteristic)

        for qt_characteristic in service.characteristics():
            _characteristic = CharacteristicInfo(service, qt_characteristic)
            assert _characteristic.uuid not in self.characteristics, 'multiple characteristics with identical unique IDs'
            self.characteristics[_characteristic.uuid] = _characteristic

        self.received.append(service)
        if len(self.received) == len(self.services):
            print('Done.')
            # we have received all the services, now we can get out of here.
            self.ready.emit()

    def _read_characteristic(self, qt_characteristic: "QLowEnergyCharacteristic", val: "QByteArray"):
        assert qt_characteristic.value() == val, 'Characteristic value does not match bytearray'
        char_uuid = qt_characteristic.uuid().toString()
        assert char_uuid in self.characteristics, f'Received QT read callback for unknown characteristic: {char_uuid}'
        callbacks = self.__callbacks[char_uuid]
        for callback in callbacks:
            self.__callbacks[char_uuid].remove(callback)
            callback(val)

        self.characteristics[char_uuid].set_characteristic(qt_characteristic)

    def _handle_service_error(self, *args):
        print(f'_handle_service_error {args}')

    def get_service_details(self):
        service = self.pending_fetch.pop(0)
        service.error.connect(self._handle_service_error)

        if service.state() == QLowEnergyService.ServiceState.DiscoveryRequired:
            service.stateChanged.connect(self.device_service_recv_details)
            callback = None
            if self.pending_fetch:
                callback = self.get_service_details

            thread_operation(Worker(lambda: service.discoverDetails()), callback=callback, start=True)
        else:
            self.device_service_recv_details(service)
            if self.pending_fetch:
                self.get_service_details()

    def device_services_retrieved(self):
        print(f'Retrieving service details..')
        self.pending_fetch = self.services[:]
        self.get_service_details()

    def name(self):
        return self.device.name()

    def device_model(self) -> str:
        return self.characteristics[PuffcoCharacteristics.MODEL].value.decode()

    @property
    def device_name(self) -> str:
        return self.characteristics[PuffcoCharacteristics.DEVICE_NAME].value.decode()

    def device_birthday(self) -> str:
        return str(datetime.fromtimestamp(int(parse(self.characteristics[PuffcoCharacteristics.BIRTHDAY].value, fmt='<I')))).split(" ")[0]

    @property
    async def operating_state(self) -> int:
        return int(float(parse(await self.read_characteristic(PuffcoCharacteristics.OPERATING_STATE))))

    @property
    async def battery_percentage(self) -> int:
        return int(float(parse(await self.read_characteristic(PuffcoCharacteristics.BATTERY_SOC))))

    @property
    async def total_dab_count(self) -> str:
        return str(int(float(parse(await self.read_characteristic(PuffcoCharacteristics.TOTAL_DAB_COUNT)))))

    @property
    async def daily_dab_count(self) -> str:
        return str(round(float(parse(await self.read_characteristic(PuffcoCharacteristics.DABS_PER_DAY))), 1))

    async def bowl_temperature(self, celsius: bool = False, as_integer: bool = False) -> str:
        heater_temp_data = parse(await self.read_characteristic(PuffcoCharacteristics.HEATER_TEMP))
        if heater_temp_data.lower() == 'nan':  # temp_celsius is nan when the atomizer is removed
            return f'--- °{"C" if celsius else "F"}'
        temp_celsius = float(heater_temp_data)

        if celsius:
            celsius = int(temp_celsius)
            if as_integer:
                return celsius
            return f'{celsius} °C'

        fahrenheit = int(((temp_celsius * 1.8) + 32))
        if as_integer:
            return fahrenheit
        return f'{fahrenheit} °F'

    @property
    async def currently_charging(self) -> tuple:
        # (0, CHARGING - BULK)
        # (1, CHARGING - TOPUP)
        # (2, NOT CHARGING - FULL, cable connected)
        # (3, NOT CHARGING - OVERTEMP)
        # (4, NOT CHARGING - CABLE DISCONNECTED)
        state = int(float(parse(await self.read_characteristic(PuffcoCharacteristics.BATTERY_CHARGE_STATE))))
        return state in (0, 1), state == 0

    def charging_eta(self) -> int:
        """
        Get the estimated seconds until the battery is fully charged
        :returns:
            None (DEVICE NOT CHARGING)
            -1 (DEVICE FULLY CHARGED ?)
            int (CHARGING; SECONDS UNTIL CHARGED)
        """
        if not self.currently_charging()[0]:
            return None

        full_eta = parse(self.characteristics[PuffcoCharacteristics.BATTERY_CHARGE_FULL_ETA].value)
        if full_eta.lower() == 'nan':
            return -1

        seconds_until_charge = float(full_eta)
        return seconds_until_charge

    def lantern_brightness(self) -> int:
        brightness = self.characteristics[PuffcoCharacteristics.LANTERN_BRIGHTNESS].value
        if brightness == 'nan':
            return 0

        # return the highest value of all the LED brightnesses
        brightness_vals = [led_brightness for led_brightness in brightness]
        return max(brightness_vals)

    def boost_settings(self) -> tuple:
        raw_boost_temp = float(parse(self.characteristics[PuffcoCharacteristics.BOOST_TEMP].value))
        raw_boost_time = float(parse(self.characteristics[PuffcoCharacteristics.BOOST_TIME].value))
        return int(round(raw_boost_temp, 2)), int(raw_boost_time)

    def send_boost_settings(self, slider: str, val: int) -> None:
        char = PuffcoCharacteristics.BOOST_TEMP if slider == 'temp' else PuffcoCharacteristics.BOOST_TIME
        return self.write_characteristic(char, struct.pack('f', val))

    @property
    async def target_temp(self) -> float:
        return float(parse(await self.read_characteristic(PuffcoCharacteristics.HEATER_TARGET_TEMP)))

    @property
    async def total_state_time(self) -> float:
        return float(parse(await self.read_characteristic(PuffcoCharacteristics.STATE_TOTAL_TIME)))

    @property
    async def elapsed_state_time(self) -> float:
        return float(parse(await self.read_characteristic(PuffcoCharacteristics.STATE_ELAPSED_TIME)))

    async def boost(self, val: float, is_time: bool = False) -> None:
        if is_time:
            char = PuffcoCharacteristics.BOOST_TIME_OVERRIDE
            total = max(await self.total_state_time, 0)
            elapsed = max(total - val, 0)
            elapsed += Constants.DABBING_ADDED_TIME
            val = elapsed
        else:
            char = PuffcoCharacteristics.BOOST_TEMP_OVERRIDE
            increment = Constants.DABBING_ADDED_TEMP_CELSIUS
            # NOTE: DABBING_ADDED_TEMP_FAHRENHEIT is unused because it causes a HUGE increase in bowl temp

            # fe((0, b.bleAddDabbingTemp)(targetTemp - profileBaseTemp + At, Ne))
            # At = DABBING_ADDED_TEMP_CELSIUS or DABBING_ADDED_TEMP_FAHRENHEIT
            # Ne = temp. unit (converts to celsius prior to sending to device)

            # target_temp is in celsius
            val = (await self.target_temp) - val + increment

        return self.write_characteristic(char, struct.pack('f', val))

    def send_lantern_animation(self, anim, enabled) -> None:
        if enabled:
            data = getattr(LanternAnimation, anim, None)
            if not data:
                return
        else:  # reset lantern color back to its original state
            data = bytearray([*self.profile_color_as_rgb(), 0, 1, 0, 0, 0])

        return self.write_characteristic(PuffcoCharacteristics.LANTERN_COLOR, data)

    def send_lantern_brightness(self, val: int) -> None:
        # clamp the value to the limitations of the device/firmware
        val = min(Constants.BRIGHTNESS_MAX, max(Constants.BRIGHTNESS_MIN, val))
        # breakdown of the brightness array: [BASE_LED, UNDER_GLASS_LED, MAIN_LED, BATT_LOGO_LED]
        return self.write_characteristic(PuffcoCharacteristics.LANTERN_BRIGHTNESS, bytearray([val] * 4))

    def send_lantern_status(self, status: bool) -> None:
        if status == self.LANTERN_ENABLED:
            return

        self.LANTERN_ENABLED = status
        return self.write_characteristic(PuffcoCharacteristics.LANTERN_STATUS, bytearray([int(status), 0, 0, 0]))

    def send_lantern_color(self, color: tuple) -> None:
        return self.write_characteristic(PuffcoCharacteristics.LANTERN_COLOR,
                                         bytearray([int(color[0]), int(color[1]), int(color[2]), 0, 1, 0, 0, 0]))

    def get_lantern_color(self) -> bytearray:
        return self.characteristics[PuffcoCharacteristics.LANTERN_COLOR].value

    async def change_profile(self, index: int, *, current: bool = False) -> None:
        await self.async_write_characteristic(PuffcoCharacteristics.PROFILE, bytearray([index, 0, 0, 0]))
        if current:
            await self.async_write_characteristic(PuffcoCharacteristics.PROFILE_CURRENT, PROFILE_TO_BYTE_ARRAY[index])

    @property
    async def profile(self) -> int:
        return int(round(float(parse(await self.read_characteristic(PuffcoCharacteristics.PROFILE_CURRENT))), 1))

    @property
    async def profile_name(self) -> str:
        return (await self.read_characteristic(PuffcoCharacteristics.PROFILE_NAME)).decode().upper()

    def set_profile_name(self, name: str) -> None:
        self.write_characteristic(PuffcoCharacteristics.PROFILE_NAME, bytearray(name.encode()))

    @property
    async def profile_temp(self) -> int:
        return int(round(float(parse(await self.read_characteristic(PuffcoCharacteristics.PROFILE_PREHEAT_TEMP))), 1))

    def set_profile_temp(self, temperature: int) -> None:
        self.write_characteristic(PuffcoCharacteristics.PROFILE_PREHEAT_TEMP, struct.pack('<f', temperature))

    @property
    async def profile_color(self) -> list:
        return list(await self.read_characteristic(PuffcoCharacteristics.PROFILE_COLOR))

    def set_profile_color(self, color_bytes: list) -> None:
        self.write_characteristic(PuffcoCharacteristics.PROFILE_COLOR, bytearray(color_bytes))

    async def profile_color_as_rgb(self, current_profile: int = None) -> (int, int, int):
        if current_profile is None:
            current_profile = await self.profile

        await self.change_profile(current_profile)
        return (await self.profile_color)[:3]

    @property
    async def profile_time(self) -> int:
        return int(round(float(parse(await self.read_characteristic(PuffcoCharacteristics.PROFILE_PREHEAT_TIME))), 1))

    def set_profile_time(self, seconds: int) -> None:
        self.write_characteristic(PuffcoCharacteristics.PROFILE_PREHEAT_TIME, struct.pack('<f', seconds))

    def send_command(self, cmd_id: int) -> None:
        return self.write_characteristic(PuffcoCharacteristics.COMMAND, struct.pack('f', cmd_id))

    def preheat(self, *, cancel=False) -> None:
        return self.send_command(DeviceCommands.HEAT_CYCLE_ABORT if cancel else DeviceCommands.HEAT_CYCLE_START)

    def stealth_mode(self) -> int:
        return int(float(parse(self.characteristics[PuffcoCharacteristics.STEALTH_STATUS].value)))

    def set_stealth_mode(self, enable: bool) -> None:
        self.write_characteristic(PuffcoCharacteristics.STEALTH_STATUS, bytearray([int(enable), 0, 0, 0]))
