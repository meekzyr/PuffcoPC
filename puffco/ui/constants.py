WIDE_SLIDER_STYLE = """
.QSlider {
    min-width: 100px;
    max-width: 100px;
    background: transparent;
}

.QSlider::groove:vertical {
    border: 1px solid #262626;
    width: 150px;
    background: #393939;
}

.QSlider::handle:vertical {
    background: #ffffff;
    height: 10px;
    margin-left: -20px;
    margin-right: -20px;
    border-radius: 30px;
}

.QSlider::add-page:vertical {
    background: #ffffff;
    border-color: #bbb;
}
"""

RAINBOW_PREVIEW_CSS = "border: 1px solid white;" \
                      'background-image: url(:/icons/rainbow.png)'
