import builtins
import os
import sys

if sys.platform == 'darwin':  # untested, not sure if necessary
    os.environ['QT_EVENT_DISPATCHER_CORE_FOUNDATION'] = '1'

from asyncio import all_tasks, ensure_future, gather, get_event_loop, Event

from PyQt5.QtGui import QFont, QFontDatabase
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QSettings

from puffco import process, initialize_settings
from puffco.ui.themes import THEMES
from puffco.ui import PuffcoMain


settings = builtins.settings = QSettings('settings.ini', QSettings.IniFormat)
if not settings.allKeys():
    initialize_settings(settings)

builtins.theme = THEMES.get(settings.value('General/Theme', 'unset', str), THEMES['basic'])

if __name__ == "__main__":
    app = QApplication([])
    QFontDatabase.addApplicationFont(':/fonts/puffco_slick.ttf')
    QFontDatabase.addApplicationFont(':/fonts/bigshoulders_medium.ttf')
    app.setFont(QFont('Big Shoulders Display Medium', 16))
    stop_event = Event()
    ensure_future(process(app, stop_event))

    ui = PuffcoMain()
    main_loop = builtins.loop = get_event_loop()
    ensure_future(ui.run(), loop=main_loop)

    try:
        main_loop.run_forever()
    except (KeyboardInterrupt, SystemExit):
        pass
    finally:
        stop_event.set()
        main_loop.run_until_complete(gather(*all_tasks(main_loop)))
        main_loop.close()
        app.quit()

    raise SystemExit(0)
