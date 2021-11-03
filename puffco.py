import builtins
import sys

from asyncio import all_tasks, CancelledError, ensure_future, get_event_loop, sleep
from datetime import datetime

from PyQt5.QtGui import QFont, QFontDatabase
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QSettings

from puffco.btnet.client import PuffcoBleakClient
from puffco.ui.themes import THEMES
from puffco.ui import PuffcoMain


class LogAndOutput:
    TIMESTAMP_FORMAT = '[%m/%d/%Y %H:%M:%S]'

    def __init__(self):
        self.console = sys.stdout
        self.log_file = open("puffco.log", "w+", encoding='utf-8')

    def close_log(self):
        if (not self.log_file) or self.log_file.closed:
            return

        print('Exiting..')
        self.log_file.close()

    def write(self, text: str):
        if not isinstance(text, str):
            return

        if self.log_file.closed:
            return

        time = datetime.now().strftime(self.TIMESTAMP_FORMAT)
        if text.rstrip():  # skip over newlines
            text = ': '.join([time, text])
        self.log_file.write(text)
        self.log_file.flush()
        self.console.write(text)

    def flush(self):  # needed for py3
        pass


async def process():
    # replacement for app._exec, allowing us to use
    # asyncio's event loops to update the UI
    while True:
        try:
            app.processEvents()
            await sleep(0)
        except (CancelledError, KeyboardInterrupt):
            break


def initialize_settings(_settings):
    _settings.beginGroup('General')
    _settings.setValue('TemperatureUnit', 'fahrenheit')  # TODO: implement
    _settings.setValue('Theme', 'unset')
    _settings.endGroup()

    _settings.beginGroup('Modes')
    _settings.setValue('Lantern', False)
    _settings.setValue('Ready', False)
    _settings.setValue('Boost', None)  # TODO (setting temp/time sliders)
    _settings.setValue('Stealth', False)
    _settings.endGroup()

    _settings.beginGroup('Home')
    _settings.setValue('HideDabCounts', False)
    _settings.endGroup()

    # TODO: think of (and implement) profile settings
    _settings.beginGroup('Profiles')
    _settings.endGroup()


builtins.settings = settings = QSettings('settings.ini', QSettings.IniFormat)
if not settings.allKeys():
    initialize_settings(settings)

logger = builtins.logger = sys.stdout = LogAndOutput()
main_loop = builtins.loop = get_event_loop()
builtins.theme = THEMES.get(settings.value('General/Theme', 'unset', str), THEMES['basic'])


if __name__ == "__main__":
    app = QApplication([])
    QFontDatabase.addApplicationFont(':/fonts/puffco_slick.ttf')
    QFontDatabase.addApplicationFont(':/fonts/bigshoulders_medium.ttf')
    app.setFont(QFont('Big Shoulders Display Medium', 16))

    builtins.client = client = PuffcoBleakClient()

    ensure_future(process())
    ensure_future(PuffcoMain(client).connect(), loop=main_loop)

    try:
        main_loop.run_forever()
    except (KeyboardInterrupt, CancelledError):
        pass
    finally:
        # stop all of our tasks:
        for task in all_tasks(main_loop):
            task.cancel()

        # flush and close our custom log handler
        logger.close_log()
        # stop our main loop, and close the app
        main_loop.stop()
        app.quit()
