# import compiled qt resource data
from puffco import resources
from asyncio import sleep

mj, mi, bu = resources.qt_version
print(f'Using Qt {mj}.{mi}.{bu}')


async def process(app, event):
    # replacement for app._exec, allowing us to use
    # asyncio's event loops to update the UI
    while not event.is_set():
        try:
            app.processEvents()
            await sleep(0)
        except (Exception, KeyboardInterrupt):
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
