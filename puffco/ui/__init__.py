import builtins
from asyncio import exceptions, ensure_future, sleep

from PyQt6.QtCore import QSize, QMetaObject, QTimer
from PyQt6.QtGui import QIcon, QPixmap, QColor
from PyQt6.QtWidgets import QPushButton, QMainWindow, QLabel
from bleak import BleakError, BleakScanner

from puffco.btnet.client import PuffcoBleakClient
from puffco.btnet import Characteristics, LoraxCharacteristics, DEVICE_HANDSHAKE_KEY, OperatingState, LanternAnimation
from .control_center import ControlCenter
from .elements import ImageButton
from .homescreen import HomeScreen
from .profiles import HeatProfiles, Profile
from .themes import DEVICE_THEME_MAP

DISABLED_BUTTON_STYLESHEET = 'QPushButton {color: gray;}'
ENABLED_BUTTON_STYLESHEET = 'QPushButton {color: white;}'
ACTIVE_TAB_STYLESHEET = 'QPushButton {text-decoration: underline;}'
INACTIVE_TAB_STYLESHEET = 'QPushButton {text-decoration: none;}'
UPDATE_COUNT = 0
CURRENT_TAB = 'home'
LAST_CHARGING_STATE = [None, None]
LAST_OPERATING_STATE = None


class PuffcoMain(QMainWindow):
    PROFILES = []
    SIZE = QSize(480, 720)
    LAST_PROFILE_ID = 0

    def __init__(self):
        self._client = None  # overridden
        super(PuffcoMain, self).__init__(parent=None)
        self.setWindowTitle("Puffco Connect (PC)")
        self.setMinimumSize(self.SIZE)
        self.setMaximumSize(self.SIZE)
        self.setMouseTracking(True)
        self.setWindowIcon(QIcon(":/icons/puffco.ico"))
        self.setStyleSheet(f"background-image: url({theme.BACKGROUND});\n"
                           f"color: rgb{theme.TEXT_COLOR};\n"
                           "border: 0px;")

        self.timer = QTimer(self)
        self.timer.setInterval(1000 * 2)  # 2s
        self.timer.timeout.connect(lambda: ensure_future(self.update_loop()).done())
        self.temp_timer = QTimer(self)
        self.temp_timer.setInterval(1000)  # 1s
        self.temp_timer.timeout.connect(lambda: ensure_future(self.update_temp()).done())

        self.puffco_icon = ImageButton(':/icons/logo.png', self, size=(64, 64),
                                       callback=lambda: self.dob.setVisible(not self.dob.isVisible()))
        self.puffco_icon.move(210, 0)

        self.control_center = ControlCenter(self)
        self.ctrl_center_btn = ImageButton(':/icons/control_center.png', self,
                                           lambda: self.control_center.setHidden(not self.control_center.isHidden()),
                                           size=(36, 36), color=QColor(*theme.TEXT_COLOR))
        self.ctrl_center_btn.move(self.width() - 70, 10)
        self.ctrl_center_btn.setDisabled(True)

        self.home = HomeScreen(self)

        self.dob = QLabel('', self.home)
        self.dob.setMinimumSize(100, 30)
        self.dob.setScaledContents(True)
        self.dob.setStyleSheet('background: transparent;')
        self.dob.move(self.home.ui_battery.x(), self.home.ui_battery.y() + 30)
        self.dob.setHidden(True)

        self.home_button = QPushButton('MY PEAK', self)
        self.home_button.setStyleSheet('QPushButton {color: gray; text-decoration: underline;}')
        self.home_button.setGeometry(0, self.height() - 70, self.width() / 2, 70)
        self.home_button.clicked.connect(lambda: self.show_tab(self.home))

        self.profiles = HeatProfiles(self)
        self.profiles.lower()
        self.profiles_button = QPushButton('HEAT PROFILES', self)
        self.profiles_button.setStyleSheet(DISABLED_BUTTON_STYLESHEET)
        self.profiles_button.setGeometry(self.home_button.width() + 2, self.home_button.y(),
                                         self.home_button.width() - 2, self.home_button.height())
        self.profiles_button.clicked.connect(lambda: self.show_tab(self.profiles))
        self.profiles_button.setDisabled(True)

        divider = QLabel('', self)
        divider.setPixmap(QPixmap(':/themes/menu_separator.png'))
        divider.setScaledContents(True)
        divider.setGeometry(-92, self.home_button.y() - 4, 573, 4)
        divider.setStyleSheet('background: transparent;')

        # draw up the home screen upon launching the app
        self.home.setVisible(True)
        self.show()

        QMetaObject.connectSlotsByName(self)

    async def update_loop(self):
        """ Update the elements on this frame (if shown) """
        if not self._client.is_connected:
            return

        global UPDATE_COUNT
        UPDATE_COUNT += 1

        try:
            lantern_settings = self.control_center.lantern_settings
            if lantern_settings.isHidden() is False and lantern_settings.wheel.selected:
                if lantern_settings.last_selection != lantern_settings.wheel.selected:
                    await self._client.send_lantern_color(lantern_settings.wheel.selected)

                lantern_settings.last_selection = lantern_settings.wheel.selected

            led = self.home.device.led
            if settings.value('Modes/Stealth', False, bool):
                if not led.isHidden():
                    led.hide()
            else:
                if led.isHidden():
                    led.show()

            operating_state = await self._client.get_operating_state()
            if operating_state not in (OperatingState.HEAT_CYCLE_PREHEAT, OperatingState.HEAT_CYCLE_ACTIVE):
                global LAST_CHARGING_STATE
                is_charging, bulk_charge = await self._client.is_currently_charging()
                if settings.value('Modes/Ready', False, bool) and (LAST_CHARGING_STATE[0] is True
                                                                   and LAST_CHARGING_STATE[0] != is_charging):
                    await self._client.preheat()

                # if we are charging, update the battery status every minute
                if (is_charging and bulk_charge) and UPDATE_COUNT % 30 == 0:
                    await self.update_battery()

                last_bulk_charge = LAST_CHARGING_STATE[1]
                if last_bulk_charge is True and (last_bulk_charge != bulk_charge):
                    self.home.ui_battery.eta.hide()

                LAST_CHARGING_STATE = is_charging, bulk_charge

            global LAST_OPERATING_STATE
            if LAST_OPERATING_STATE != operating_state:
                # Handle operating state changes:
                if LAST_OPERATING_STATE:
                    last_state_name = OperatingState(LAST_OPERATING_STATE).name
                    curr_state_name = OperatingState(operating_state).name
                    print(f'(DEBUG) OpState changed {last_state_name} --> {curr_state_name}')
                    if LAST_OPERATING_STATE in (OperatingState.HEAT_CYCLE_PREHEAT, OperatingState.HEAT_CYCLE_ACTIVE):
                        # we just came out of a heat cycle
                        await self.update_battery()

                        # slow our temp reader, and make sure it is started/active
                        # it will automatically stop once it hits 100*F
                        self.temp_timer.setInterval(1000 * 3)
                        if not self.temp_timer.isActive():
                            self.temp_timer.start()

                        # lets update the dab count
                        if not settings.value('Home/HideDabCounts', False, bool):
                            total = await self._client.get_total_dab_count()
                            if self.home.ui_total_dab_cnt.data != total:  # check if our dab count has changed
                                self.home.ui_total_dab_cnt.update_data(total)
                                # we can update the daily avg as well
                                self.home.ui_daily_dab_cnt.update_data(await self._client.get_daily_dab_count())

                        if operating_state not in (OperatingState.HEAT_CYCLE_PREHEAT, OperatingState.HEAT_CYCLE_ACTIVE):
                            active_prof_window = self.profiles.active_profile
                            if active_prof_window and active_prof_window.started:
                                active_prof_window.cycle_finished()

                LAST_OPERATING_STATE = operating_state

            # Current operating state handling:
            if operating_state == OperatingState.TEMP_SELECT:
                current_profile_id = await self._client.get_profile()
                if self.LAST_PROFILE_ID != current_profile_id:
                    await self._client.change_profile(current_profile_id)
                    if self.LAST_PROFILE_ID:
                        profile_name = await self._client.get_profile_name(self.LAST_PROFILE_ID)
                        if profile_name and self.home.ui_active_profile.data != profile_name:
                            self.home.ui_active_profile.update_data(profile_name)
                            self.home.device.colorize(*await self._client.profile_color_as_rgb())

                    self.LAST_PROFILE_ID = current_profile_id

            elif operating_state in (OperatingState.HEAT_CYCLE_PREHEAT, OperatingState.HEAT_CYCLE_ACTIVE):
                self.temp_timer.setInterval(1000)
                if not self.temp_timer.isActive():
                    self.temp_timer.start()

            elif operating_state == OperatingState.HEAT_CYCLE_FADE:
                # we are fresh out of a heat cycle, lets update the battery display and slow our temperature updates
                self.temp_timer.setInterval(1000 * 3)
                await self.update_battery()

        except BleakError:
            # device is not connected, or our characteristics have not been populated
            pass

    async def update_temp(self):
        if not self._client.is_connected:
            return

        try:
            temp = await self._client.get_bowl_temperature()
            num = ''.join(filter(str.isdigit, temp))
            if not num:
                # atomizer is disconnected, check for changes every 20s
                self.temp_timer.setInterval(1000 * 20)
            elif int(num) <= 100:
                #  we are at/below 100 Fahrenheit.. stop our ival
                self.temp_timer.stop()

            active_prof_window = self.profiles.active_profile
            if not active_prof_window:
                profile_id = await self._client.get_profile()
                self.profiles.select_profile(profile_id)
                active_prof_window = self.profiles.active_profile
                active_prof_window.verified = True

            if active_prof_window:
                if not active_prof_window.verified:
                    profile_id = await self._client.get_profile()
                    if profile_id != active_prof_window.idx:
                        self.profiles.select_profile(profile_id)
                        active_prof_window = self.profiles.active_profile

                    active_prof_window.verified = True

                if LAST_OPERATING_STATE in (OperatingState.HEAT_CYCLE_PREHEAT, OperatingState.HEAT_CYCLE_ACTIVE) and \
                        not active_prof_window.started:
                    # adjust the UI if we have not already done so
                    active_prof_window.start(send_command=False)

                active_prof_window.update_temp_reading(temp)

            if temp and self.home.ui_bowl_temp.data != temp:
                self.home.ui_bowl_temp.update_data(temp)

        except BleakError:
            pass

    async def update_battery(self):
        if not self._client.is_connected:
            return

        try:
            percentage = await self._client.get_battery_percentage()
            is_charging, _ = await self._client.is_currently_charging()
            eta = None
            if is_charging:
                eta = await self._client.get_battery_charge_eta()
                hr, rem = divmod(eta, 3600)
                mins, sec = divmod(rem, 60)
                eta = f'{str(int(mins)).zfill(2)}:{str(int(sec)).zfill(2)}'
                if hr > 0:
                    eta = str(int(hr)).zfill(2) + f':{eta}'

            self.home.ui_battery.update_battery(percentage, is_charging, eta)
        except BleakError:
            pass

    def show_tab(self, frame):
        global CURRENT_TAB
        is_home = frame == self.home
        if (is_home and CURRENT_TAB == 'home') or (CURRENT_TAB == 'profiles' and not is_home):
            return

        CURRENT_TAB = 'home' if is_home else 'profiles'
        other = self.profiles if is_home else self.home

        self.home_button.setStyleSheet(ACTIVE_TAB_STYLESHEET if is_home else INACTIVE_TAB_STYLESHEET)
        self.profiles_button.setStyleSheet(ACTIVE_TAB_STYLESHEET if not is_home else INACTIVE_TAB_STYLESHEET)
        self.home_button.setDown(is_home)
        self.profiles_button.setDown(not is_home)

        # update the data
        try:
            fetch_task = ensure_future(frame.fill())
            fetch_task.done()
        except BleakError:
            # no connect (typically happens when reading a characteristic in the same frame as establishing connection)
            return self.show_tab(frame)

        frame.show()
        frame.setVisible(True)
        other.hide()  # hide the other frame to prevent element bleed
        other.setVisible(False)

    async def connect(self, *, retry=False):
        if not retry:
            print('Scanning for Peak Pro devices..')

        if PuffcoBleakClient.RETRIES >= 100:
            raise ConnectionRefusedError('Could not connect to any devices.')

        found_device_addr, found_device_name = '', ''
        connected, timeout = False, False

        self.home.update_connection_status('SCANNING', 'yellow')
        discovered_devices_and_advertisement_data = await BleakScanner().discover(return_adv=True)
        for key, dev_and_adv_dat in discovered_devices_and_advertisement_data.items():
            device = dev_and_adv_dat[0]
            adv_dat = dev_and_adv_dat[1]

            if device.address.startswith('84:2E:14:') or device.address.startswith('84:FD:27:') or \
                    Characteristics.SERVICE_UUID in adv_dat.service_uuids:
                self.home.update_connection_status(f'Found "{device.name}"', 'orange')
                print(f'Potential Peak Pro "{device.name}" ({device.address})')
                found_device_name = device.name
                found_device_addr = device.address
                break

        if not found_device_addr:
            print('Could not locate a Peak Pro, rescanning..')
            return await self.connect(retry=True)

        self._client = PuffcoBleakClient(found_device_addr,
                                         disconnected_callback=lambda *args: ensure_future(self.on_disconnect(*args)))
        error = False
        try:
            self.home.update_connection_status(f'Connecting to "{found_device_name}"', 'orange')
            connected = await self._client.connect(timeout=3, use_cached=not retry)
            if connected:
                self._client.DEVICE_NAME = found_device_name
                self._client.DEVICE_MAC_ADDRESS = found_device_addr

                success = False
                lorax_service = self._client.services.get_service(LoraxCharacteristics.LORAX_SERVICE_UUID)
                if lorax_service:
                    success = await self._client.init_lorax_proto()
                    if not success:
                        connected = False

                else:
                    try:
                        device_fw_rev = (await self._client.read_gatt_char(Characteristics.SOFTWARE_REVISION)).decode()
                    except (OSError, BleakError):
                        device_fw_rev = None

                    if device_fw_rev is None:
                        self.home.update_connection_status(f'Connection Error', 'red')
                        print('Error retrieving firmware revision, disconnecting.')
                        await self._client.disconnect()
                        self._client = None
                        return await self.connect(retry=True)

                    elif device_fw_rev == 'X':
                        self.home.update_connection_status(f'Authenticating..', 'yellow')

                        current_access_seed = list(await self._client.read_gatt_char(Characteristics.ACCESS_SEED_KEY))
                        sliced_key = self._client.create_auth_token(current_access_seed, DEVICE_HANDSHAKE_KEY)

                        # now we write this sliced key to the accessSeed characteristic, which should grant R/W perms
                        # for the remainder of the characteristics
                        try:
                            await self._client.write_gatt_char(Characteristics.ACCESS_SEED_KEY, sliced_key)
                            success = True
                        except (BleakError, OSError):
                            raise RuntimeError(f'Failed to authenticate to device (Firmware: {device_fw_rev})')

                if success:
                    await self._on_connect()
        except exceptions.TimeoutError:  # could not connect to device
            print('Timed out while connecting, retrying..')
            timeout = error = True
        except BleakError as e:  # could not find device
            print(f'(ERROR: BLEAK) "{e}", retrying..')
            error = True

        if self.home.ui_connect_status.text() != 'DISCONNECTED' and not connected:
            self.home.update_connection_status('DISCONNECTED', 'red')

        if connected and (error is False):
            await self._client.pair()
            self._client.RETRIES = 0
            print('Connected!')
            self.home.update_connection_status('CONNECTED', '#4CD964')
            return connected
        else:
            if retry:
                self._client.RETRIES += 1

            if not timeout:
                print('Failed to connect, retrying..')

            await sleep(2.5)  # reconnectDelayMs: 2500
            return await self.connect(retry=True)

    async def on_disconnect(self, client: PuffcoBleakClient):
        await self.home.reset()
        if not self.isVisible():
            self.show()

        if self.timer.isActive():
            self.timer.stop()

        print(f'Lost connection to "{client.DEVICE_NAME}" ({client.DEVICE_MAC_ADDRESS}), attempting to reconnect...')
        return await self.connect(retry=True)

    async def _on_connect(self):
        self.timer.start()
        # Set the app theme (upon first launch):
        self.home_button.setStyleSheet(ENABLED_BUTTON_STYLESHEET)
        self.profiles_button.setStyleSheet(ENABLED_BUTTON_STYLESHEET)
        self.ctrl_center_btn.setDisabled(False)
        self.dob.setText(f'DOB: {await self._client.get_device_birthday()}')

        if settings.value('General/Theme', 'unset', str) == 'unset':
            model = await self._client.get_device_model()
            if model not in DEVICE_THEME_MAP:
                print(f'Unknown device model {model}')
                builtins.theme = theme = DEVICE_THEME_MAP['0']  # basic/default
            else:
                builtins.theme = theme = DEVICE_THEME_MAP[model]

            settings.setValue('General/Theme', theme.name)
            if theme.name != 'basic':
                self.setStyleSheet(f"background-image: url({theme.BACKGROUND});\n"
                                   f"color: rgb{theme.TEXT_COLOR};\n"
                                   "border: 0px;")

                pixmap = self.ctrl_center_btn.alter_pixmap(self.ctrl_center_btn.path, size=(36, 36),
                                                           paint=True, color=QColor(*theme.TEXT_COLOR))
                self.ctrl_center_btn.setIconSize(pixmap.size())
                self.ctrl_center_btn.setIcon(QIcon(pixmap))

                self.home.device.device.setPixmap(QPixmap(theme.DEVICE))
                self.home.device.device.resize(291, 430)

                self.home.device.led.setMaximumWidth(self.home.device.device.width() - theme.LIGHTING_WIDTH_ADJ)
                self.home.device.led.setPixmap(QPixmap(theme.LIGHTING))
                self.home.device.led.resize(self.home.device.device.width() - theme.LIGHTING_WIDTH_ADJ,
                                            self.home.device.device.height())
                if self.home.device.color:
                    self.home.device.colorize(*self.home.device.color)

                for button in self.profiles.profile_buttons.values():
                    button._pixmap = QPixmap(theme.HOME_DATA)
                    button.update()

        self.control_center.lantern_brightness.blockSignals(True)
        self.control_center.lantern_brightness.setValue(await self._client.get_lantern_brightness())
        self.control_center.lantern_brightness.blockSignals(False)

        boost_temp, boost_time = await self._client.get_boost_settings(self.LAST_PROFILE_ID)
        self.control_center.boost_settings.temp_slider.setValue(boost_temp)
        self.control_center.boost_settings.time_slider.setValue(boost_time)

        # Activate control center buttons:
        for control in self.control_center.CONTROLS:
            value = settings.value(control.setting_name, False, bool)

            if 'lantern' in control.setting_name.lower():
                # send the lantern status and continue. we do not want to activate the button,
                # as that will cause the lantern UI to appear upon opening control center
                await self._client.send_lantern_status(value)

                lantern_color = await self._client.get_lantern_color()
                if lantern_color in LanternAnimation.all:  # lantern is an animation preset, toggle the button!
                    idx = LanternAnimation.all.index(lantern_color)
                    self.control_center.lantern_settings.animation_toggle(['PULSING', 'ROTATING', 'DISCO_MODE'][idx])
                else:
                    rgb = tuple(lantern_color[:3])
                    self.control_center.lantern_settings.wheel.selected = rgb
                    self.control_center.lantern_settings.preview.setStyleSheet(f'background: rgb{rgb};'
                                                                               f'border: 1px solid white;')

                control.ENABLED = not value
                control.on_click(update_setting=False)
                continue

            if value:
                control.on_click()

        current_profile_name = await self._client.get_profile_name(self.LAST_PROFILE_ID)

        reset_idx = None
        # loop through the 4 profiles; fetching and storing the data for each of them
        for i in range(0, 4):
            await self._client.change_profile(i)
            name = await self._client.get_profile_name(i)
            if current_profile_name == name:
                reset_idx = i

            temp = await self._client.get_profile_temp(i)
            color_bytes = await self._client.get_profile_color(i)
            time = await self._client.get_profile_time(i)

            self.PROFILES.append(Profile(i, name, temp, time, color_bytes[:3], color_bytes))
            await sleep(0.1)  # short delay to prevent incorrect profile colors

        # reset the profile back to where it was
        if reset_idx is not None:
            await self._client.change_profile(reset_idx, current=True)

        if self.profiles.isVisible():
            self.profiles.setVisible(False)

        await self.profiles.fill()
        await self.home.fill(from_callback=True)
        if not self.isVisible():
            self.show()

        self.profiles_button.setDisabled(False)

    def closeEvent(self, event):
        logger.close_log()
        loop.stop()
        event.accept()
