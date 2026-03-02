"""Processing provider registration."""

from qgis.core import QgsProcessingProvider

from .algorithms.shadow_hours import ComputeWtgAnnualShadowHoursAlgorithm


class WtgShadowProcessingProvider(QgsProcessingProvider):
    def id(self):
        return "wtgshadow"

    def name(self):
        return "WTG Shadow"

    def longName(self):
        return self.name()

    def loadAlgorithms(self):
        self.addAlgorithm(ComputeWtgAnnualShadowHoursAlgorithm())
