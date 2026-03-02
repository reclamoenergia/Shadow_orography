"""QGIS plugin entry point for WTG Shadow Hours."""


def classFactory(iface):
    from .plugin import WtgShadowHoursPlugin

    return WtgShadowHoursPlugin(iface)
