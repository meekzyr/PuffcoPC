# import compiled qt resource data
from puffco import resources

mj, mi, bu = resources.qt_version
print(f'Using Qt {mj}.{mi}.{bu}')


def nuitka_patch_winrt():
    import winrt
    try:
        winrt._winrt.__file__
    except AttributeError:
        from pathlib import Path

        def _import_ns_module(ns):
            import importlib.machinery
            import importlib.util

            try:
                module_name = "_winrt_" + ns.replace('.', '_')
                # hotfix for packing winrt on windows
                file = str(Path(__file__).parent) + '\_winrt.pyd'

                loader = importlib.machinery.ExtensionFileLoader(module_name, file)
                spec = importlib.util.spec_from_loader(module_name, loader)
                module = importlib.util.module_from_spec(spec)
                loader.exec_module(module)
                return module
            except:
                return None

        winrt._import_ns_module = _import_ns_module
