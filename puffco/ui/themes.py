from puffco.btnet import PeakProModels
DEVICE_THEME_MAP = {}
THEMES = {}


class Theme:
    BACKGROUND = ':/assets/basic_background.png'
    DEVICE = ':/assets/basic_peak.png'
    LIGHTING = ':/assets/basic_lighting.png'
    HOME_DATA = ':/assets/basic_home_data.png'
    LIGHTING_WIDTH_ADJ = 50  # this is subtracted
    TEXT_COLOR = (255, 255, 255)


class Basic(Theme):
    name = 'basic'


class Opal(Theme):
    name = 'opal'
    BACKGROUND = Basic.BACKGROUND.replace('basic', 'opal')
    DEVICE = Basic.DEVICE.replace('basic', 'opal')
    LIGHTING = Basic.LIGHTING.replace('basic', 'opal')
    HOME_DATA = Basic.HOME_DATA.replace('basic', 'opal')
    LIGHTING_WIDTH_ADJ = 0
    TEXT_COLOR = (0, 0, 0)
    # TODO: Fix up this theme
    #  * I do not have an Opal Peak, so I cannot replicate the UI


THEMES['basic'] = Basic()
THEMES['opal'] = Opal()

for (idx, name) in PeakProModels.items():
    if 'opal' in name.lower():
        theme = THEMES['opal']
    else:
        theme = THEMES['basic']

    DEVICE_THEME_MAP[idx] = DEVICE_THEME_MAP[name] = theme
