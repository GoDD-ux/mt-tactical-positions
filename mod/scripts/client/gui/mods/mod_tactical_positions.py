from gui.tactical_positions import minimap

_original = None


def init():
    global _original
    _original = minimap.install()
    minimap.getIndex()


def fini():
    if _original is not None:
        minimap.uninstall(_original)
