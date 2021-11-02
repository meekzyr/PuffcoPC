python3 -m nuitka --standalone --plugin-no-detection --nofollow-imports --enable-plugin=pyqt5 --include-qt-plugins=platforms --python-flag=no_site --include-package=puffco --include-package=bleak --include-package=PIL --include-package=dbus_next --enable-plugin=anti-bloat --noinclude-setuptools-mode=nofollow --noinclude-pytest-mode=nofollow --remove-output puffco.py
python3 tools/prepare_dist.py
