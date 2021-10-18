# import compiled qt resource data
__import__('resources')

if __name__ == "__main__":
    from asyncio import get_event_loop, new_event_loop
    from PyQt5.QtGui import QFont, QFontDatabase
    from PyQt5.QtWidgets import QApplication

    app = QApplication([])
    QFontDatabase.addApplicationFont(':/fonts/assets/puffco-slick.ttf')
    app.setFont(QFont('Slick'))

    main_loop = get_event_loop()
    bleak_loop = new_event_loop()

    from puffco.ui import PuffcoMain
    ui = PuffcoMain('84:2E:14:80:2B:5A', main_loop, bleak_loop)
    ui.show()

    try:
        app.exec_()
    except KeyboardInterrupt:
        pass
    finally:
        if main_loop.is_running():
            main_loop.stop()
        main_loop.close()
        app.quit()
