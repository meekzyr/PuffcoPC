import builtins

from asyncio import ensure_future

from PyQt5.QtCore import QSize, QMetaObject, QTimer
from PyQt5.QtGui import QIcon, QPixmap, QColor
from PyQt5.QtWidgets import QPushButton, QMainWindow, QLabel

from puffco.bluetooth.constants import *
from .control_center import ControlCenter
from .elements import ImageButton
from .homescreen import HomeScreen
from .profiles import HeatProfiles, Profile
from .themes import DEVICE_THEME_MAP

from puffco.bluetooth import BluetoothHandle

UPDATE_COUNT = 0
CURRENT_TAB = 'home'
LAST_CHARGING_STATE = [None, None]
LAST_OPERATING_STATE = None
LAST_PROFILE_ID = None


def _ensure_future(*args):
    try:
        fut = ensure_future(*args)
    except RuntimeError:
        fut = None
    return fut


class PuffcoMain(QMainWindow):
    PROFILES = []
    SIZE = QSize(480, 720)

    def __init__(self):
        super(PuffcoMain, self).__init__(parent=None)
        self.setWindowTitle("Puffco Connect (PC)")
        self.setMinimumSize(self.SIZE)
        self.setMaximumSize(self.SIZE)
        self.setMouseTracking(True)
        self.setWindowIcon(QIcon(":/icons/puffco.ico"))
        self.setStyleSheet(f"background-image: url({theme.BACKGROUND});\n"
                           f"color: rgb{theme.TEXT_COLOR};\n"
                           "border: 0px;")

        self.bluetooth = builtins.client = BluetoothHandle(callback=lambda: _ensure_future(self.on_connect()))
        self.bluetooth.controller.disconnected.connect(lambda: _ensure_future(self.on_disconnect()))

        self.timer = QTimer(self)
        self.timer.setInterval(1000 * 2)  # 2s

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
        self.home_button.setGeometry(0, self.height() - 70, self.width() / 2, 70)
        self.home_button.clicked.connect(lambda: _ensure_future(self.show_tab(self.home)))

        self.profiles = HeatProfiles(self)
        self.profiles.lower()
        self.profiles_button = QPushButton('HEAT PROFILES', self)
        self.profiles_button.setGeometry(self.home_button.width() + 2, self.home_button.y(),
                                         self.home_button.width() - 2, self.home_button.height())
        self.profiles_button.clicked.connect(lambda: _ensure_future(self.show_tab(self.profiles)))
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
        if not self.bluetooth.is_connected:
            return

        global UPDATE_COUNT
        UPDATE_COUNT += 1

        lantern_settings = self.control_center.lantern_settings
        if lantern_settings.isHidden() is False and lantern_settings.wheel.selected:
            if lantern_settings.last_selection != lantern_settings.wheel.selected:
                self.bluetooth.device().send_lantern_color(lantern_settings.wheel.selected)

            lantern_settings.last_selection = lantern_settings.wheel.selected

        led = self.home.device.led
        if settings.value('Modes/Stealth', False, bool):
            if not led.isHidden():
                led.hide()
        else:
            if led.isHidden():
                led.show()

        operating_state = await self.bluetooth.device().operating_state
        if operating_state not in (OperatingState.HEAT_CYCLE_PREHEAT, OperatingState.HEAT_CYCLE_ACTIVE):
            global LAST_CHARGING_STATE
            is_charging, bulk_charge = await self.bluetooth.device().currently_charging
            if settings.value('Modes/Ready', False, bool) and (LAST_CHARGING_STATE[0] is True
                                                               and LAST_CHARGING_STATE[0] != is_charging):
                self.bluetooth.device().preheat()

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

                    # lets update the dab count
                    if not settings.value('Home/HideDabCounts', False, bool):
                        total = await self.bluetooth.device().total_dab_count
                        if self.home.ui_total_dab_cnt.data != total:  # check if our dab count has changed
                            self.home.ui_total_dab_cnt.update_data(total)
                            # we can update the daily avg as well
                            self.home.ui_daily_dab_cnt.update_data(await self.bluetooth.device().daily_dab_count)

                    if operating_state not in (OperatingState.HEAT_CYCLE_PREHEAT, OperatingState.HEAT_CYCLE_ACTIVE):
                        active_prof_window = self.profiles.active_profile
                        if active_prof_window and active_prof_window.started:
                            active_prof_window.cycle_finished()

            LAST_OPERATING_STATE = operating_state

        # Current operating state handling:
        if operating_state == OperatingState.TEMP_SELECT:
            global LAST_PROFILE_ID
            current_profile_id = await self.bluetooth.device().profile
            if LAST_PROFILE_ID != current_profile_id:
                await self.bluetooth.device().change_profile(current_profile_id)
                if LAST_PROFILE_ID:
                    profile_name = await self.bluetooth.device().profile_name
                    if profile_name and self.home.ui_active_profile.data != profile_name:
                        self.home.ui_active_profile.update_data(profile_name)
                        self.home.device.colorize(*await self.bluetooth.device().profile_color_as_rgb())

                LAST_PROFILE_ID = current_profile_id

        elif operating_state in (OperatingState.HEAT_CYCLE_PREHEAT, OperatingState.HEAT_CYCLE_ACTIVE):
            await self.update_temp()

        elif operating_state == OperatingState.HEAT_CYCLE_FADE:
            # we are fresh out of a heat cycle, lets update the battery display and slow our temperature updates
            await self.update_battery()

    async def update_temp(self):
        if not self.bluetooth.is_connected:
            return

        temp = await self.bluetooth.device().bowl_temperature()
        num = ''.join(filter(str.isdigit, temp))
        if not num:
            # atomizer is disconnected, check for changes every 20s
            return

        active_prof_window = self.profiles.active_profile
        if not active_prof_window:
            self.profiles.select_profile(await self.bluetooth.device().profile)
            active_prof_window = self.profiles.active_profile
            active_prof_window.verified = True

        if active_prof_window:
            if not active_prof_window.verified:
                profile_id = await self.bluetooth.device().profile
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

    async def update_battery(self):
        if not self.bluetooth.is_connected:
            return

        is_charging, _ = await self.bluetooth.device().currently_charging
        eta = None
        if is_charging:
            eta = self.bluetooth.device().charging_eta
            hr, rem = divmod(eta, 3600)
            mins, sec = divmod(rem, 60)
            eta = f'{str(int(mins)).zfill(2)}:{str(int(sec)).zfill(2)}'
            if hr > 0:
                eta = str(int(hr)).zfill(2) + f':{eta}'

        self.home.ui_battery.update_battery(await self.bluetooth.device().battery_percentage, is_charging, eta)

    async def show_tab(self, frame):
        global CURRENT_TAB
        is_home = frame == self.home
        if (is_home and CURRENT_TAB == 'home') or (CURRENT_TAB == 'profiles' and not is_home):
            return

        CURRENT_TAB = 'home' if is_home else 'profiles'
        other = self.profiles if is_home else self.home

        self.home_button.setDown(is_home)
        self.profiles_button.setDown(not is_home)

        await frame.fill()
        frame.show()
        frame.setVisible(True)
        # hide the other frame to prevent element bleeding
        other.hide()
        other.setVisible(False)

    async def on_disconnect(self):
        print('on_disconnect')
        await self.home.reset()
        if not self.isVisible():
            self.show()

        if self.timer.isActive():
            self.timer.stop()

        print(f'Lost connection to device, attempting to reconnect...')
        await self.connect(retry=True)

    async def on_connect(self):
        self.bluetooth.connected = True
        self.timer.timeout.connect(lambda: _ensure_future(self.update_loop()))
        self.timer.start()

        device = self.bluetooth.device()
        self.ctrl_center_btn.setDisabled(False)
        self.dob.setText(f'DOB: {device.get_cached_char_data(PuffcoCharacteristics.BIRTHDAY)}')
        # Set the app theme (upon first launch):
        if settings.value('General/Theme', 'unset', str) == 'unset':
            model = device.device_model()
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
        self.control_center.lantern_brightness.setValue(device.lantern_brightness())
        self.control_center.lantern_brightness.blockSignals(False)

        boost_temp, boost_time = device.boost_settings()
        self.control_center.boost_settings.temp_slider.setValue(boost_temp)
        self.control_center.boost_settings.time_slider.setValue(boost_time)

        # Activate control center buttons:
        for control in self.control_center.CONTROLS:
            value = settings.value(control.setting_name, False, bool)

            if 'lantern' in control.setting_name.lower():
                # send the lantern status and continue. we do not want to activate the button,
                # as that will cause the lantern UI to appear upon opening control center
                device.send_lantern_status(value)

                lantern_color = device.get_lantern_color()
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

        await self.profiles.retrieve_profiles()
        await self.home.fill(from_callback=True)

        if not self.isVisible():
            self.show()

    def closeEvent(self, event):
        self.blockSignals(True)
        loop.stop()
        event.accept()

    async def run(self):
        self.bluetooth.start()
