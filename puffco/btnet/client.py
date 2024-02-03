import builtins
import math
import contextlib
from asyncio import Event, ensure_future, TimeoutError, wait_for
from datetime import datetime
from typing import Union


from hashlib import sha256

from bleak import BleakClient, BleakError

from . import *
from .buffer import Buffer

PROFILE_TO_BYTE_ARRAY = {0: bytearray([0, 0, 0, 0]),
                         1: bytearray([0, 0, 128, 63]),
                         2: bytearray([0, 0, 0, 64]),
                         3: bytearray([0, 0, 64, 64])}


REVISION_CHARS = "ABCDEFGHJKMNPRTUVWXYZ"


class PuffcoBleakClient(BleakClient):
    DEVICE_NAME, DEVICE_MAC_ADDRESS, RETRIES = '', None, 0
    LANTERN_ENABLED, LANTERN_COLOR = None, None

    SEQUENCE_ID = 0
    USE_LORAX_PROTOCOL, LORAX_PROTO_VER = False, None
    MAX_PAYLOAD, MAX_FILES, MAX_CMDS = 0, 0, 0  # received from getLimits opcode

    def __init__(self, device_mac_addr, **kwargs):
        builtins.client = self
        self.transactions = {}
        self.transaction_responses = {}
        super(PuffcoBleakClient, self).__init__(device_mac_addr, **kwargs)

    async def write_gatt_char(self, char, data: Union[bytes, bytearray], *, response: bool = None, number=0) -> None:
        if char in (Characteristics.LANTERN_COLOR, LoraxCharacteristics.LANTERN_COLOR):
            self.LANTERN_COLOR = data

        if self.USE_LORAX_PROTOCOL:
            if char not in LoraxCharacteristics.PROTOCOL_CHARS:
                lorax_path = CHAR_UUID2LORAX_PATH[char]
                if '%N' in lorax_path:
                    lorax_path = lorax_path.replace('%N', str(number))

                if lorax_path.startswith('/u/app/hc/') and lorax_path.endswith('/colr'):
                    return await self.write(lorax_path, data)

                return await self.write_short(lorax_path, data)

        return await super(PuffcoBleakClient, self).write_gatt_char(char, data, response=response)

    async def read_gatt_char(self, char, **kwargs) -> bytearray:
        if self.USE_LORAX_PROTOCOL:
            if char in LoraxCharacteristics.PROTOCOL_CHARS:
                data = await super(PuffcoBleakClient, self).read_gatt_char(char, **kwargs)
            else:
                lorax_path = CHAR_UUID2LORAX_PATH[char]
                if '%N' in lorax_path:
                    index = kwargs.pop('number', 0)
                    if index is None:
                        index = 0

                    lorax_path = lorax_path.replace('%N', str(index))

                data = await self.read_short(lorax_path)
        else:
            data = await super(PuffcoBleakClient, self).read_gatt_char(char, **kwargs)

        if char in (Characteristics.LANTERN_COLOR, LoraxCharacteristics.LANTERN_COLOR):
            self.LANTERN_COLOR = data

        return data

    @staticmethod
    def create_auth_token(access_seed, handshake_key):
        new_key = bytearray(32)

        for i in range(0, 16):  # add handshake key to first 16 bits; add current ACCESS_SEED_KEY to last 16 bits
            new_key[i] = handshake_key[i]
            new_key[i + 16] = access_seed[i]

        digested_key = sha256(new_key).hexdigest()  # hash the new bytearray
        # slice the digested key (we only want first 16 bits)
        return bytearray([int(digested_key[i:i + 2], 16) for i in range(0, len(digested_key), 2)][0:16])

    # LORAX (New Protocol)

    def get_next_sequence_id(self):
        self.SEQUENCE_ID = (self.SEQUENCE_ID + 1) % 65535
        return self.SEQUENCE_ID

    @staticmethod
    def make_command(bc, bd, be):
        buf = Buffer(3)
        buf.writeUInt16LE(bc, 0)
        buf.writeUInt8(bd, 2)
        if be:
            return buf.data + be
        return buf.data

    async def send_lorax_command(self, cmd):
        await self.write_gatt_char(LoraxCharacteristics.LORAX_COMMAND, cmd, response=False)

    async def lorax_reply(self, _characteristic, data):  # loraxReplyHandler
        buffer = Buffer(data)
        sequence_id = buffer.readUInt16LE(0)
        bu = buffer.readUInt8(2)

        transaction = self.transactions.get(sequence_id, None)
        if not transaction:
            print(f'Lorax replied with unrecognized sequenceId: {sequence_id}')
            if transaction['flag']:  # callback is asyncio.Event.set
                self.transaction_responses[f"{sequence_id}-{transaction['path']}"] = None
                transaction['deferred']()  # set flag
            return

        opcode = transaction['opcode']
        path = transaction['path']
        if bu:
            print(f'Lorax replied with error "{bu}" for seq {sequence_id}  op: {opcode}  path: {path}')
            if transaction['flag']:  # callback is asyncio.Event.set
                self.transaction_responses[f"{sequence_id}-{transaction['path']}"] = None
                transaction['deferred']()  # set flag
            return

        data = data[3:]
        if path == LoraxCharacteristics.SOFTWARE_REVISION:
            rev = int(parse(data, fmt='<I'))

            if (not isinstance(rev, int)) or rev < 0:
                rev_string = rev
            elif rev == 0:
                rev_string = "X*"
            else:
                i = rev - 1
                rev_string = ""
                while i >= 0:
                    rev_string = REVISION_CHARS[i % len(REVISION_CHARS)] + rev_string
                    i = math.floor(i / len(REVISION_CHARS)) - 1

            data = rev_string

        callback = transaction['deferred']
        if transaction['flag']:  # callback is asyncio.Event.set
            self.transaction_responses[f"{sequence_id}-{transaction['path']}"] = data
            return callback()  # set flag

        callback_args = transaction['args']
        if callback is not None:
            if callback_args is None:
                callback_args = ()

            await callback(data, *callback_args)

    @staticmethod
    def lorax_event(*args, **kwargs):  # TODO: loraxEventHandler (do i even need this?)
        print('lorax_event', args, kwargs)

    async def init_lorax_proto(self):
        try:
            await self.start_notify(LoraxCharacteristics.LORAX_REPLY, self.lorax_reply)
            await self.start_notify(LoraxCharacteristics.LORAX_EVENT, self.lorax_event)
        except (OSError, BleakError):
            return False

        self.USE_LORAX_PROTOCOL = True
        self.LORAX_PROTO_VER = parse(await self.read_gatt_char(LoraxCharacteristics.LORAX_VERSION), fmt='H')

        flag = Event()

        async def proto_limits_recv(data):
            buf = Buffer(data)
            self.MAX_PAYLOAD = buf.readUInt16LE(0)
            self.MAX_FILES = buf.readUInt16LE(2)
            self.MAX_CMDS = buf.readUInt16LE(4)
            # send (and await) auth response
            await self.send_lorax_auth(flag)

        # get protocol limits
        proto_limits_tx = self.make_transaction(LoraxOpCodes.GET_LIMITS, None, None, callback=proto_limits_recv)
        await self.send_lorax_command(proto_limits_tx['cmd'])
        with contextlib.suppress(TimeoutError):
            await wait_for(flag.wait(), timeout=1)

        return True

    @staticmethod
    def write_short_cmd(ag, ah, ai, aj):
        if isinstance(ai, str):
            ai = bytearray(ai.encode())

        ak = Buffer(3)
        ak.writeUInt16LE(ag, 0)
        ak.writeUInt8(ah, 2)
        return ak.data + ai + bytearray(1) + aj

    async def write_short(self, char_path, data):
        bo = 0  # unsure of what this is but it is always zero
        if char_path.endswith('/name'):
            bp = 4  # I do not want to reverse the entire `writeCommand` function
        else:
            bp = 0

        bs = self.write_short_cmd(bo, bp, char_path, data)
        write_tx = self.make_transaction(LoraxOpCodes.WRITE_SHORT, char_path, bs)
        await self.send_lorax_command(write_tx['cmd'])

    @staticmethod
    def write_cmd(ag, ah, ai):
        if isinstance(ai, str):
            ai = bytearray(ai.encode())

        aj = Buffer(4)
        aj.writeUInt16LE(ag, 0)
        aj.writeUInt16LE(ah, 2)
        return aj.data + ai

    async def write(self, char_path, data):
        bs = self.write_cmd(0, 0, data)
        write_tx = self.make_transaction(LoraxOpCodes.WRITE, char_path, bs)
        await self.send_lorax_command(write_tx['cmd'])

    @staticmethod
    def read_short_cmd(ag, ah, ai):
        if isinstance(ai, str):
            ai = bytearray(ai.encode())

        aj = Buffer(3)
        aj.writeUInt16LE(ag, 0)
        aj.writeUInt16LE(ah, 2)
        return aj.data + ai

    async def read_short(self, char_path):
        bm = 0  # not sure what this is supposed to be, but it is always 0
        bp = self.read_short_cmd(bm, self.MAX_PAYLOAD, char_path)
        resp = Event()
        read_tx = self.make_transaction(LoraxOpCodes.READ_SHORT, char_path, bp, callback=resp.set, flag=True)
        ensure_future(self.write_gatt_char(LoraxCharacteristics.LORAX_COMMAND, read_tx['cmd'], response=False))
        await resp.wait()
        return self.transaction_responses.pop(f"{read_tx['sequenceId']}-{char_path}")

    def make_transaction(self, op_code, char_path, bf, callback=None, args=None, flag=False):
        tx_id = self.get_next_sequence_id()
        cmd_data = self.make_command(tx_id, op_code, bf)

        transaction = {
            'sequenceId': tx_id,
            'opcode': op_code,
            'path': char_path or "",
            'cmd': cmd_data,
            'deferred': callback,
            'args': args,
            'flag': flag,
        }

        self.transactions[tx_id] = transaction
        return transaction

    async def send_lorax_auth(self, flag):
        async def auth_done(*_args):
            flag.set()

        async def unlock_access(access_seed):
            new_key = bytearray(32)

            for i in range(0, 16):  # add handshake key to first 16 bits; add current ACCESS_SEED_KEY to last 16 bits
                new_key[i] = DEVICE_HANDSHAKE2_KEY[i]
                new_key[i + 16] = access_seed[i]

            digested_key = sha256(new_key).hexdigest()  # hash the new bytearray
            # slice the digested key (we only want first 16 bits)
            sliced_key = bytearray([int(digested_key[i:i + 2], 16) for i in range(0, len(digested_key), 2)][0:16])

            unlock_tx = self.make_transaction(LoraxOpCodes.UNLOCK_ACCESS, None, sliced_key, callback=auth_done)
            await self.write_gatt_char(LoraxCharacteristics.LORAX_COMMAND, unlock_tx['cmd'], response=False)

        # send the getAccessSeed opcode, and follow up with unlockAccess after receiving the access seed
        get_seed_tx = self.make_transaction(LoraxOpCodes.GET_ACCESS_SEED, None, None, callback=unlock_access)
        await self.write_gatt_char(LoraxCharacteristics.LORAX_COMMAND, get_seed_tx['cmd'], response=False)

    #
    async def send_mode_command(self, command: int):
        if self.USE_LORAX_PROTOCOL:
            data = command.to_bytes(1, 'little')
        else:
            data = struct.pack('f', command)

        await self.write_gatt_char(Characteristics.MODE_COMMAND, data)

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
        state = await self.read_gatt_char(Characteristics.BATTERY_CHARGE_STATE)
        if self.USE_LORAX_PROTOCOL:
            state = int.from_bytes(state, 'little')
        else:
            state = int(float(parse(state)))
        return state in (0, 1), state == 0

    async def preheat(self, cancel=False) -> None:
        await self.send_mode_command(DeviceCommands.HEAT_CYCLE_ABORT if cancel else DeviceCommands.HEAT_CYCLE_START)

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
        return (await self.get_profile_color(current_profile))[:3]

    async def change_profile(self, profile: int, *, current: bool = False) -> None:
        if not self.USE_LORAX_PROTOCOL:
            await self.write_gatt_char(Characteristics.PROFILE, bytearray([profile, 0, 0, 0]))

        if current:
            if self.USE_LORAX_PROTOCOL:
                data = profile.to_bytes(1, 'little')
            else:
                data = PROFILE_TO_BYTE_ARRAY[profile]

            await self.write_gatt_char(Characteristics.PROFILE_CURRENT, data)

    async def get_profile(self) -> int:
        profile_num = await self.read_gatt_char(Characteristics.PROFILE_CURRENT)
        if self.USE_LORAX_PROTOCOL:
            return int.from_bytes(profile_num, 'little')

        return int(round(float(parse(profile_num)), 1))

    async def set_profile_name(self, name: str, i: int) -> None:
        await self.write_gatt_char(Characteristics.PROFILE_NAME, bytearray(name.encode()), number=i)

    async def get_profile_name(self, i) -> str:
        profile_name = await self.read_gatt_char(Characteristics.PROFILE_NAME, number=i)
        if profile_name is None:
            return '<empty>'

        return profile_name.decode().upper()

    async def set_profile_color(self, color_bytes: list, i: int):
        await self.write_gatt_char(Characteristics.PROFILE_COLOR, bytearray(color_bytes), number=i)

    async def get_profile_color(self, i) -> [bytes]:
        color_data = await self.read_gatt_char(Characteristics.PROFILE_COLOR, number=i)
        return list(color_data)  # getting hex code: codecs.encode(color_data, 'hex').decode()[:6]

    async def set_profile_time(self, seconds: int, i: int) -> None:
        packed_time = struct.pack('<f', seconds)
        return await self.write_gatt_char(Characteristics.PROFILE_PREHEAT_TIME, packed_time, number=i)

    async def get_profile_time(self, i) -> int:
        time_data = parse(await self.read_gatt_char(Characteristics.PROFILE_PREHEAT_TIME, number=i))
        return int(round(float(time_data), 1))

    async def set_profile_temp(self, temperature: int, i: int) -> None:
        packed_temperature = struct.pack('<f', temperature)
        return await self.write_gatt_char(Characteristics.PROFILE_PREHEAT_TEMP, packed_temperature, number=i)

    async def get_profile_temp(self, i) -> int:
        temperature_data = parse(await self.read_gatt_char(Characteristics.PROFILE_PREHEAT_TEMP, number=i))
        return int(round(float(temperature_data), 1))

    async def get_operating_state(self) -> int:  # see btnet.OperatingStates
        data = await self.read_gatt_char(Characteristics.OPERATING_STATE)
        if self.USE_LORAX_PROTOCOL:
            return int.from_bytes(data, 'little')

        operating_state = parse(data)
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
        if self.USE_LORAX_PROTOCOL:
            data = bytearray([int(status)])
        else:
            data = bytearray([int(status), 0, 0, 0])

        await self.write_gatt_char(Characteristics.LANTERN_STATUS, data)

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
        else:  # reset lantern color back to its original state
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

    async def get_boost_settings(self, i) -> (int, int):
        raw_boost_temp = await self.read_gatt_char(Characteristics.BOOST_TEMP, number=i)
        raw_boost_time = await self.read_gatt_char(Characteristics.BOOST_TIME, number=i)
        return int(float(parse(raw_boost_temp))), int(float(parse(raw_boost_time)))
