from bleak import BleakClient
from . import Characteristics, parse

import struct


class PuffcoBleakClient(BleakClient):
    def __init__(self, mac_address, **kwargs):
        super(PuffcoBleakClient, self).__init__(mac_address, **kwargs)
        self.loop = kwargs.pop('loop')

    async def get_battery_percentage(self):
        raw_percent_data = await self.read_gatt_char(Characteristics.BATTERY_SOC)
        current_percent = int(float(parse(raw_percent_data)))
        return f'{current_percent} %'

    async def get_total_dab_count(self):
        raw_dab_total = await self.read_gatt_char(Characteristics.TOTAL_DAB_COUNT)
        return str(int(float(parse(raw_dab_total))))

    async def get_daily_dab_count(self):
        raw_dpd_data = await self.read_gatt_char(Characteristics.DABS_PER_DAY)
        return str(round(float(parse(raw_dpd_data)), 1))

    async def get_bowl_temperature(self, celsius=False):
        heater_temp_data = await self.read_gatt_char(Characteristics.HEATER_TEMP)
        temp_celsius = float(parse(heater_temp_data))
        if celsius:
            celsius = int(temp_celsius)
            return f'{celsius} °C'

        fahrenheit = int(((temp_celsius * 1.8) + 32))
        return f'{fahrenheit} °F'

    async def get_device_name(self):
        device_name = await self.read_gatt_char(Characteristics.DEVICE_NAME)
        return device_name.decode()

    async def profile_colour_as_rgb(self):
        current_profile = await self.get_profile()
        await self.change_profile(current_profile)
        return (await self.get_profile_colour())[:3]

    async def write_gatt_char(self, *args, **kwargs):
        kwargs['response'] = True
        return await super(PuffcoBleakClient, self).write_gatt_char(*args, **kwargs)

    async def change_profile(self, profile: int):
        await self.write_gatt_char(Characteristics.PROFILE,
                                   bytearray([profile, 0, 0, 0]))

    async def get_profile(self):
        profile = parse(await self.read_gatt_char(Characteristics.PROFILE_CURRENT))
        return int(round(float(profile), 1))

    async def get_profile_name(self):
        profile_name = await self.read_gatt_char(Characteristics.PROFILE_NAME)
        return profile_name.decode().upper()

    async def get_profile_colour(self):
        colour_data = await self.read_gatt_char(Characteristics.PROFILE_COLOUR)
        return list(colour_data)

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
            5 - OFF
            6 - ON
            7 - PREHEATING
            8 - HEATED
        """
        operating_state = parse(await self.read_gatt_char(Characteristics.OPERATING_STATE))
        return int(float(operating_state))
