from bleak import BleakClient
from . import Characteristics, PeakProModels, parse, parseInt

from datetime import datetime
import struct

PROFILE_TO_BYT_ARRAY = {0: bytearray([0, 0, 0, 0]),
                        1: bytearray([0, 0, 128, 63]),
                        2: bytearray([0, 0, 0, 64]),
                        3: bytearray([0, 0, 64, 64])}


class PuffcoBleakClient(BleakClient):
    attempted_devices = []

    def __init__(self, **kwargs):
        super(PuffcoBleakClient, self).__init__('', **kwargs)

    async def get_device_model(self, *, return_name=False) -> str:  # TODO: tie this into changing app bg/device visualization
        model_number = (await self.read_gatt_char(Characteristics.MODEL_NUMBER)).decode()
        if return_name:
            return PeakProModels.get(model_number, 'UNKNOWN MODEL')
        return model_number

    @property
    async def currently_charging(self):
        # (0, CHARGING - BULK)
        # (1, CHARGING - TOPUP)
        # (2, NOT CHARGING - FULL, cable connected)
        # (3, NOT CHARGING - OVERTEMP)
        # (4, NOT CHARGING - CABLE DISCONNECTED)
        state = int(float(parse(await self.read_gatt_char(Characteristics.BATTERY_CHARGE_STATE))))
        return state in (0, 1)

    async def preheat(self):
        await self.write_gatt_char(Characteristics.COMMAND, bytearray([0, 0, 224, 64]))

    async def get_battery_charge_eta(self):
        """
        Get the estimated seconds until the battery is fully charged
        :returns:
            None (DEVICE NOT CHARGING)
            -1 (DEVICE FULLY CHARGED ?)
            int (CHARGING; SECONDS UNTIL CHARGED)
        """
        if not (await self.currently_charging):
            return None

        full_eta = parse(await self.read_gatt_char(Characteristics.BATTERY_CHARGE_FULL_ETA))
        if full_eta.lower() == 'nan':
            return -1

        seconds_until_charge = float(full_eta)
        return seconds_until_charge

    async def get_battery_percentage(self):
        raw_percent_data = await self.read_gatt_char(Characteristics.BATTERY_SOC)
        return int(float(parse(raw_percent_data)))

    async def get_total_dab_count(self):
        raw_dab_total = await self.read_gatt_char(Characteristics.TOTAL_DAB_COUNT)
        return str(int(float(parse(raw_dab_total))))

    async def get_daily_dab_count(self):
        raw_dpd_data = await self.read_gatt_char(Characteristics.DABS_PER_DAY)
        return str(round(float(parse(raw_dpd_data)), 1))

    async def get_bowl_temperature(self, celsius=False):
        heater_temp_data = parse(await self.read_gatt_char(Characteristics.HEATER_TEMP))
        if heater_temp_data.lower() == 'nan':  # temp_celsius is nan when the atomizer is removed
            return f'- - °{"C" if celsius else "F"}'
        temp_celsius = float(heater_temp_data)

        if celsius:
            celsius = int(temp_celsius)
            return f'{celsius} °C'

        fahrenheit = int(((temp_celsius * 1.8) + 32))
        return f'{fahrenheit} °F'

    async def get_device_name(self):
        device_name = await self.read_gatt_char(Characteristics.DEVICE_NAME)
        return device_name.decode()

    async def profile_color_as_rgb(self, current_profile: int = None):
        if current_profile is None:
            current_profile = await self.get_profile()

        await self.change_profile(current_profile)
        return (await self.get_profile_color())[:3]

    async def write_gatt_char(self, *args, **kwargs):
        kwargs['response'] = True
        return await super(PuffcoBleakClient, self).write_gatt_char(*args, **kwargs)

    async def change_profile(self, profile: int, *, current: bool = False):
        await self.write_gatt_char(Characteristics.PROFILE,
                                   bytearray([profile, 0, 0, 0]))
        if current:
            await self.write_gatt_char(Characteristics.PROFILE_CURRENT,
                                       PROFILE_TO_BYT_ARRAY[profile])

    async def get_profile(self):
        profile = parse(await self.read_gatt_char(Characteristics.PROFILE_CURRENT))
        return int(round(float(profile), 1))

    async def set_profile_name(self, name: str):
        await self.write_gatt_char(Characteristics.PROFILE_NAME, bytearray(name.encode()))

    async def get_profile_name(self):
        profile_name = await self.read_gatt_char(Characteristics.PROFILE_NAME)
        return profile_name.decode().upper()

    async def set_profile_color(self, color_bytes: list):
        await self.write_gatt_char(Characteristics.PROFILE_COLOR, bytearray(color_bytes))

    async def get_profile_color(self):
        color_data = await self.read_gatt_char(Characteristics.PROFILE_COLOR)
        return list(color_data)  # getting hex code: codecs.encode(color_data, 'hex').decode()[:6]

    async def set_profile_time(self, seconds: int):
        packed_time = struct.pack('<f', seconds)
        return await self.write_gatt_char(Characteristics.PROFILE_PREHEAT_TIME, packed_time)

    async def get_profile_time(self):
        time_data = parse(await self.read_gatt_char(Characteristics.PROFILE_PREHEAT_TIME))
        return int(round(float(time_data), 1))

    async def set_profile_temp(self, temperature: int):
        packed_temperature = struct.pack('<f', temperature)
        return await self.write_gatt_char(Characteristics.PROFILE_PREHEAT_TEMP, packed_temperature)

    async def get_profile_temp(self):
        temperature_data = parse(await self.read_gatt_char(Characteristics.PROFILE_PREHEAT_TEMP))
        return int(round(float(temperature_data), 1))

    async def get_operating_state(self) -> int:
        """
        Operating States:
            0 - "INIT_MEMORY"
            1 - "INIT_VERSION_DISP"
            2 - "INIT_BATTERY_DISP"
            3 - "MASTER_OFF"
            4 - SLEEP
            5 - OFF "IDLE
            6 - ON "TEMP SELECT"
            7 - PREHEATING
            8 - HEATED "CYCLE_ACTIVE"
            9 - COOLDOWN "CYCLE_FADE"
            10 - "VERSION_DISP"
            11 - "BATTERY_DISP"
            12 - "FACTORY TEST"
            13 - BLE BONDING
        """
        operating_state = parse(await self.read_gatt_char(Characteristics.OPERATING_STATE))
        return int(float(operating_state))

    async def get_device_birthday(self):
        birthday = await self.read_gatt_char(Characteristics.DEVICE_BIRTHDAY)
        datetime_time = datetime.fromtimestamp(int(parseInt(birthday)))
        return str(datetime_time).split(" ")[0]
