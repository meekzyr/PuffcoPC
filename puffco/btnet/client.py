import struct
from datetime import datetime
from typing import Union

from bleak import BleakClient

from . import Characteristics, Constants, LanternAnimation, PeakProModels, parse

PROFILE_TO_BYT_ARRAY = {0: bytearray([0, 0, 0, 0]),
                        1: bytearray([0, 0, 128, 63]),
                        2: bytearray([0, 0, 0, 64]),
                        3: bytearray([0, 0, 64, 64])}


class PuffcoBleakClient(BleakClient):
    RETRIES = 0
    LANTERN_ENABLED = None
    LANTERN_COLOR = None

    attempted_devices = []
    name = ''  # name of the connected device

    def __init__(self, **kwargs):
        super(PuffcoBleakClient, self).__init__('', **kwargs)

    async def write_gatt_char(self, char, data: Union[bytes, bytearray]) -> None:
        if char == Characteristics.LANTERN_COLOR:
            self.LANTERN_COLOR = data

        return await super(PuffcoBleakClient, self).write_gatt_char(char, data, response=True)

    async def read_gatt_char(self, char, **kwargs) -> bytearray:
        data = await super(PuffcoBleakClient, self).read_gatt_char(char, **kwargs)
        if char == Characteristics.LANTERN_COLOR:
            self.LANTERN_COLOR = data

        return data

    async def get_device_model(self, *, return_name=False) -> str:
        model_number = (await self.read_gatt_char(Characteristics.MODEL_NUMBER)).decode()
        if return_name:
            return PeakProModels.get(model_number, 'UNKNOWN MODEL')
        return model_number

    async def is_currently_charging(self) -> (bool, bool):
        # (0, CHARGING - BULK)
        # (1, CHARGING - TOPUP)
        # (2, NOT CHARGING - FULL, cable connected)
        # (3, NOT CHARGING - OVERTEMP)
        # (4, NOT CHARGING - CABLE DISCONNECTED)
        state = int(float(parse(await self.read_gatt_char(Characteristics.BATTERY_CHARGE_STATE))))
        return state in (0, 1), state == 0

    async def power_off(self) -> None:
        await self.write_gatt_char(Characteristics.COMMAND, bytearray([0, 0, 0, 0]))

    async def preheat(self, cancel=False) -> None:
        if cancel:
            byte_arr = bytearray([0, 0, 0, 65])  # heatCycleAbort
        else:
            byte_arr = bytearray([0, 0, 224, 64])  # heatCycleStart
        await self.write_gatt_char(Characteristics.COMMAND, byte_arr)

    async def get_battery_charge_eta(self):
        """
        Get the estimated seconds until the battery is fully charged
        :returns:
            None (DEVICE NOT CHARGING)
            -1 (DEVICE FULLY CHARGED ?)
            int (CHARGING; SECONDS UNTIL CHARGED)
        """
        if not (await self.is_currently_charging())[0]:
            return None

        full_eta = parse(await self.read_gatt_char(Characteristics.BATTERY_CHARGE_FULL_ETA))
        if full_eta.lower() == 'nan':
            return -1

        seconds_until_charge = float(full_eta)
        return seconds_until_charge

    async def get_battery_percentage(self) -> int:
        raw_percent_data = await self.read_gatt_char(Characteristics.BATTERY_SOC)
        return int(float(parse(raw_percent_data)))

    async def get_total_dab_count(self) -> str:
        raw_dab_total = await self.read_gatt_char(Characteristics.TOTAL_DAB_COUNT)
        return str(int(float(parse(raw_dab_total))))

    async def get_daily_dab_count(self) -> str:
        raw_dpd_data = await self.read_gatt_char(Characteristics.DABS_PER_DAY)
        return str(round(float(parse(raw_dpd_data)), 1))

    async def get_bowl_temperature(self, celsius=False, integer=False) -> str:
        heater_temp_data = parse(await self.read_gatt_char(Characteristics.HEATER_TEMP))
        if heater_temp_data.lower() == 'nan':  # temp_celsius is nan when the atomizer is removed
            return f'--- °{"C" if celsius else "F"}'
        temp_celsius = float(heater_temp_data)

        if celsius:
            celsius = int(temp_celsius)
            if integer:
                return celsius
            return f'{celsius} °C'

        fahrenheit = int(((temp_celsius * 1.8) + 32))
        if integer:
            return fahrenheit
        return f'{fahrenheit} °F'

    async def get_device_name(self) -> str:
        device_name = await self.read_gatt_char(Characteristics.DEVICE_NAME)
        return device_name.decode()

    async def profile_color_as_rgb(self, current_profile: int = None) -> (int, int, int):
        if current_profile is None:
            current_profile = await self.get_profile()

        await self.change_profile(current_profile)
        return (await self.get_profile_color())[:3]

    async def change_profile(self, profile: int, *, current: bool = False) -> None:
        await self.write_gatt_char(Characteristics.PROFILE,
                                   bytearray([profile, 0, 0, 0]))
        if current:
            await self.write_gatt_char(Characteristics.PROFILE_CURRENT,
                                       PROFILE_TO_BYT_ARRAY[profile])

    async def get_profile(self) -> int:
        profile = parse(await self.read_gatt_char(Characteristics.PROFILE_CURRENT))
        return int(round(float(profile), 1))

    async def set_profile_name(self, name: str) -> None:
        await self.write_gatt_char(Characteristics.PROFILE_NAME, bytearray(name.encode()))

    async def get_profile_name(self) -> str:
        profile_name = await self.read_gatt_char(Characteristics.PROFILE_NAME)
        return profile_name.decode().upper()

    async def set_profile_color(self, color_bytes: list):
        await self.write_gatt_char(Characteristics.PROFILE_COLOR, bytearray(color_bytes))

    async def get_profile_color(self) -> [bytes]:
        color_data = await self.read_gatt_char(Characteristics.PROFILE_COLOR)
        return list(color_data)  # getting hex code: codecs.encode(color_data, 'hex').decode()[:6]

    async def set_profile_time(self, seconds: int) -> None:
        packed_time = struct.pack('<f', seconds)
        return await self.write_gatt_char(Characteristics.PROFILE_PREHEAT_TIME, packed_time)

    async def get_profile_time(self) -> int:
        time_data = parse(await self.read_gatt_char(Characteristics.PROFILE_PREHEAT_TIME))
        return int(round(float(time_data), 1))

    async def set_profile_temp(self, temperature: int) -> None:
        packed_temperature = struct.pack('<f', temperature)
        return await self.write_gatt_char(Characteristics.PROFILE_PREHEAT_TEMP, packed_temperature)

    async def get_profile_temp(self) -> int:
        temperature_data = parse(await self.read_gatt_char(Characteristics.PROFILE_PREHEAT_TEMP))
        return int(round(float(temperature_data), 1))

    async def get_operating_state(self) -> int:  # see btnet.OperatingStates
        operating_state = parse(await self.read_gatt_char(Characteristics.OPERATING_STATE))
        return int(float(operating_state))

    async def get_device_birthday(self) -> str:
        birthday = await self.read_gatt_char(Characteristics.DEVICE_BIRTHDAY)
        datetime_time = datetime.fromtimestamp(int(parse(birthday, fmt='<I')))
        return str(datetime_time).split(" ")[0]

    async def set_stealth_mode(self, enable: bool) -> None:
        await self.write_gatt_char(Characteristics.STEALTH_STATUS, bytearray([int(enable), 0, 0, 0]))

    async def get_stealth_mode(self) -> int:
        mode = await self.read_gatt_char(Characteristics.STEALTH_STATUS)
        return int(float(parse(mode)))

    async def get_target_temp(self) -> float:
        return float(parse(await self.read_gatt_char(Characteristics.HEATER_TARGET_TEMP)))

    async def boost(self, val: float, is_time: bool = False) -> None:
        if is_time:
            char = Characteristics.TIME_OVERRIDE
            total = max(await self.get_state_ttime(), 0)
            elapsed = max(total - val, 0)
            elapsed += Constants.DABBING_ADDED_TIME
            val = elapsed
        else:
            char = Characteristics.TEMPERATURE_OVERRIDE
            target_temp = await self.get_target_temp()  # celsius
            increment = Constants.DABBING_ADDED_TEMP_CELSIUS
            # NOTE: DABBING_ADDED_TEMP_FAHRENHEIT is unused because it causes a HUGE increase in bowl temp

            # fe((0, b.bleAddDabbingTemp)(targetTemp - profileBaseTemp + At, Ne))
            # At = DABBING_ADDED_TEMP_CELSIUS or DABBING_ADDED_TEMP_FAHRENHEIT
            # Ne = temp. unit (converts to celsius prior to sending to device)
            val = target_temp - val + increment

        await self.write_gatt_char(char, struct.pack('f', val))

    async def get_state_etime(self) -> float:
        return float(parse(await self.read_gatt_char(Characteristics.STATE_ELAPSED_TIME)))

    async def get_state_ttime(self) -> float:
        return float(parse(await self.read_gatt_char(Characteristics.STATE_TOTAL_TIME)))

    async def send_lantern_status(self, status: bool) -> None:
        if status == self.LANTERN_ENABLED:
            return

        self.LANTERN_ENABLED = status
        await self.write_gatt_char(Characteristics.LANTERN_STATUS, bytearray([int(status), 0, 0, 0]))

    async def get_lantern_color(self) -> bytearray:
        return await self.read_gatt_char(Characteristics.LANTERN_COLOR)

    async def send_lantern_color(self, color) -> None:
        await self.write_gatt_char(Characteristics.LANTERN_COLOR,
                                   bytearray([int(color[0]), int(color[1]), int(color[2]), 0, 1, 0, 0, 0]))

    async def send_lantern_animation(self, anim, enabled) -> None:
        if enabled:
            data = getattr(LanternAnimation, anim, None)
            if not data:
                return
        else:  # reset lantern color back to it's original state
            data = bytearray([*await self.profile_color_as_rgb(), 0, 1, 0, 0, 0])

        await self.write_gatt_char(Characteristics.LANTERN_COLOR, data)

    async def send_lantern_brightness(self, val: int) -> None:
        # clamp the value to the limitations of the device/firmware
        val = min(Constants.BRIGHTNESS_MAX, max(Constants.BRIGHTNESS_MIN, val))
        # breakdown of the brightness array: [BASE_LED, UNDER_GLASS_LED, MAIN_LED, BATT_LOGO_LED]
        await self.write_gatt_char(Characteristics.LANTERN_BRIGHTNESS, bytearray([val] * 4))

    async def get_lantern_brightness(self) -> int:
        brightness_data = await self.read_gatt_char(Characteristics.LANTERN_BRIGHTNESS)
        # return the highest value, since the LEDs will always have the same brightness
        return max(brightness_data)

    async def send_boost_settings(self, slider: str, val: int) -> None:
        characteristic = Characteristics.BOOST_TEMP if slider == 'temp' else Characteristics.BOOST_TIME
        await self.write_gatt_char(characteristic, struct.pack('f', val))

    async def get_boost_settings(self) -> (int, int):
        raw_boost_temp = await self.read_gatt_char(Characteristics.BOOST_TEMP)
        raw_boost_time = await self.read_gatt_char(Characteristics.BOOST_TIME)
        return int(float(parse(raw_boost_temp))), int(float(parse(raw_boost_time)))
