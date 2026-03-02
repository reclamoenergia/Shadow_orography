"""Plugin bootstrap wiring for QGIS."""

from .processing_provider import WtgShadowProcessingProvider


class WtgShadowHoursPlugin:
    def __init__(self, iface):
        self.iface = iface
        self.provider = None

    def initGui(self):
        self.provider = WtgShadowProcessingProvider()
        from qgis.core import QgsApplication

        QgsApplication.processingRegistry().addProvider(self.provider)

    def unload(self):
        if self.provider is not None:
            from qgis.core import QgsApplication

            QgsApplication.processingRegistry().removeProvider(self.provider)
            self.provider = None
