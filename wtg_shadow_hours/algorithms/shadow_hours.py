"""QGIS Processing algorithm for annual WTG shadow hours."""

from __future__ import annotations

import os

import numpy as np
from osgeo import gdal, osr
from qgis.core import (
    QgsColorRampShader,
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransform,
    QgsFeatureRequest,
    QgsProcessing,
    QgsProcessingAlgorithm,
    QgsProcessingException,
    QgsProcessingParameterEnum,
    QgsProcessingParameterField,
    QgsProcessingParameterNumber,
    QgsProcessingParameterRasterDestination,
    QgsProcessingParameterVectorLayer,
    QgsProject,
    QgsRasterLayer,
    QgsRasterShader,
    QgsSingleBandPseudoColorRenderer,
)
from qgis.PyQt.QtGui import QColor

from ..core import Turbine, accumulate_shadow_hours, generate_yearly_timestamps, solar_position_noaa


class ComputeWtgAnnualShadowHoursAlgorithm(QgsProcessingAlgorithm):
    INPUT = "INPUT"
    ROTOR_FIELD = "ROTOR_FIELD"
    HUB_FIELD = "HUB_FIELD"
    MIN_SOLAR_ELEV = "MIN_SOLAR_ELEV"
    YEAR = "YEAR"
    TIMESTEP = "TIMESTEP"
    CELLSIZE = "CELLSIZE"
    BUFFER = "BUFFER"
    OUTPUT_RASTER = "OUTPUT_RASTER"

    TIMESTEP_OPTIONS = [5, 10, 15, 30]
    CELLSIZE_OPTIONS = [10.0, 20.0, 25.0, 50.0]

    def name(self):
        return "compute_wtg_annual_shadow_hours"

    def displayName(self):
        return "Compute WTG annual shadow hours"

    def group(self):
        return "WTG Shadow"

    def groupId(self):
        return "wtg_shadow"

    def shortHelpString(self):
        return "Computes annual worst-case wind turbine shadow hours on a flat terrain."

    def initAlgorithm(self, config=None):
        self.addParameter(
            QgsProcessingParameterVectorLayer(
                self.INPUT,
                "Input turbines layer",
                [QgsProcessing.TypeVectorPoint],
            )
        )
        self.addParameter(
            QgsProcessingParameterField(
                self.ROTOR_FIELD,
                "Rotor diameter field (m)",
                type=QgsProcessingParameterField.Numeric,
                parentLayerParameterName=self.INPUT,
            )
        )
        self.addParameter(
            QgsProcessingParameterField(
                self.HUB_FIELD,
                "Hub height field (m)",
                type=QgsProcessingParameterField.Numeric,
                parentLayerParameterName=self.INPUT,
            )
        )
        self.addParameter(
            QgsProcessingParameterNumber(self.MIN_SOLAR_ELEV, "Min solar elevation (deg)", defaultValue=0.0)
        )
        self.addParameter(QgsProcessingParameterNumber(self.YEAR, "Year", type=QgsProcessingParameterNumber.Integer, defaultValue=2025))
        self.addParameter(
            QgsProcessingParameterEnum(
                self.TIMESTEP,
                "Timestep (minutes)",
                options=[str(v) for v in self.TIMESTEP_OPTIONS],
                defaultValue=2,
            )
        )
        self.addParameter(
            QgsProcessingParameterEnum(
                self.CELLSIZE,
                "Cell size (m)",
                options=[str(int(v)) for v in self.CELLSIZE_OPTIONS],
                defaultValue=1,
            )
        )
        self.addParameter(QgsProcessingParameterNumber(self.BUFFER, "Buffer (m)", defaultValue=2000.0))
        self.addParameter(QgsProcessingParameterRasterDestination(self.OUTPUT_RASTER, "Output raster"))

    def processAlgorithm(self, parameters, context, feedback):
        layer = self.parameterAsVectorLayer(parameters, self.INPUT, context)
        if layer is None:
            raise QgsProcessingException("Input point layer is required.")
        if layer.crs().isGeographic():
            raise QgsProcessingException("Input layer uses geographic coordinates (degrees). Reproject to a metric projected CRS first.")

        rotor_field = self.parameterAsString(parameters, self.ROTOR_FIELD, context)
        hub_field = self.parameterAsString(parameters, self.HUB_FIELD, context)
        min_elev = self.parameterAsDouble(parameters, self.MIN_SOLAR_ELEV, context)
        year = self.parameterAsInt(parameters, self.YEAR, context)
        timestep_minutes = self.TIMESTEP_OPTIONS[self.parameterAsEnum(parameters, self.TIMESTEP, context)]
        cellsize_m = self.CELLSIZE_OPTIONS[self.parameterAsEnum(parameters, self.CELLSIZE, context)]
        buffer_m = self.parameterAsDouble(parameters, self.BUFFER, context)
        output_path = self.parameterAsOutputLayer(parameters, self.OUTPUT_RASTER, context)

        if layer.featureCount() == 0:
            raise QgsProcessingException("Input layer has no features.")

        has_turbine_id = layer.fields().indexFromName("turbine_id") >= 0
        turbines = []
        req = QgsFeatureRequest()
        for feat in layer.getFeatures(req):
            geom = feat.geometry()
            if geom.isEmpty():
                continue
            pt = geom.asPoint()
            rotor = float(feat[rotor_field])
            hub = float(feat[hub_field])
            if rotor <= 0 or hub <= 0:
                continue
            turbine_id = str(feat["turbine_id"]) if has_turbine_id else str(feat.id())
            turbines.append(Turbine(pt.x(), pt.y(), rotor, hub, turbine_id))

        if not turbines:
            raise QgsProcessingException("No valid turbines found (positive rotor diameter and hub height required).")

        x_vals = np.array([t.x for t in turbines])
        y_vals = np.array([t.y for t in turbines])
        xmin = float(x_vals.min() - buffer_m)
        xmax = float(x_vals.max() + buffer_m)
        ymin = float(y_vals.min() - buffer_m)
        ymax = float(y_vals.max() + buffer_m)

        n_cols = int(np.ceil((xmax - xmin) / cellsize_m))
        n_rows = int(np.ceil((ymax - ymin) / cellsize_m))
        x_coords = xmin + (np.arange(n_cols) + 0.5) * cellsize_m
        y_coords = ymax - (np.arange(n_rows) + 0.5) * cellsize_m

        src_crs = layer.crs()
        x_center = (xmin + xmax) * 0.5
        y_center = (ymin + ymax) * 0.5
        center_ll = QgsCoordinateTransform(src_crs, QgsCoordinateReferenceSystem("EPSG:4326"), QgsProject.instance()).transform(x_center, y_center)

        times = generate_yearly_timestamps(year, timestep_minutes, timezone="Europe/Rome")
        azimuth_deg, elevation_deg = solar_position_noaa(times, center_ll.y(), center_ll.x())

        timestep_hours = timestep_minutes / 60.0
        feedback.pushInfo(f"Computing {len(times)} timesteps on grid {n_cols}x{n_rows}.")
        shadow_hours = accumulate_shadow_hours(
            x_coords=x_coords,
            y_coords=y_coords,
            turbines=turbines,
            azimuth_deg=azimuth_deg,
            elevation_deg=elevation_deg,
            timestep_hours=timestep_hours,
            min_solar_elevation_deg=min_elev,
        )

        final_path = self._write_raster(output_path, shadow_hours, xmin, ymax, cellsize_m, src_crs)
        self._add_styled_raster(final_path)
        return {self.OUTPUT_RASTER: final_path}

    def createInstance(self):
        return ComputeWtgAnnualShadowHoursAlgorithm()

    def _write_raster(self, path, array, xmin, ymax, cellsize, crs):
        tif_path = path if os.path.splitext(path)[1].lower() != ".asc" else os.path.splitext(path)[0] + ".tif"
        driver = gdal.GetDriverByName("GTiff")
        dataset = driver.Create(tif_path, array.shape[1], array.shape[0], 1, gdal.GDT_Float32)
        if dataset is None:
            raise QgsProcessingException(f"Could not create output raster: {tif_path}")
        dataset.SetGeoTransform((xmin, cellsize, 0.0, ymax, 0.0, -cellsize))
        srs = osr.SpatialReference()
        srs.ImportFromWkt(crs.toWkt())
        dataset.SetProjection(srs.ExportToWkt())
        band = dataset.GetRasterBand(1)
        band.WriteArray(array)
        band.SetNoDataValue(-9999.0)
        band.FlushCache()
        dataset.FlushCache()
        dataset = None

        if os.path.splitext(path)[1].lower() == ".asc":
            gdal.Translate(path, tif_path, format="AAIGrid")
            return path
        return tif_path

    def _add_styled_raster(self, path):
        layer = QgsRasterLayer(path, "Annual shadow hours")
        if not layer.isValid():
            return
        provider = layer.dataProvider()
        stats = provider.bandStatistics(1)

        shader = QgsRasterShader()
        color_ramp = QgsColorRampShader()
        color_ramp.setColorRampType(QgsColorRampShader.Interpolated)
        color_ramp.setColorRampItemList(
            [
                QgsColorRampShader.ColorRampItem(0.0, QColor("#f7fbff"), "0"),
                QgsColorRampShader.ColorRampItem(stats.maximumValue * 0.5, QColor("#6baed6"), "mid"),
                QgsColorRampShader.ColorRampItem(max(stats.maximumValue, 1.0), QColor("#08306b"), "max"),
            ]
        )
        shader.setRasterShaderFunction(color_ramp)
        renderer = QgsSingleBandPseudoColorRenderer(provider, 1, shader)
        layer.setRenderer(renderer)
        layer.setName("Annual shadow hours")
        QgsProject.instance().addMapLayer(layer)
