"""PySide6 desktop application for Shadow Orography Studio."""

from __future__ import annotations

import json
import importlib
import importlib.util
import sys
import tempfile
import traceback
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QImage, QPainter, QPen, QPolygonF
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QGraphicsEllipseItem,
    QGraphicsPolygonItem,
    QGraphicsScene,
    QGraphicsView,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSlider,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)
from shapely.geometry import Polygon

from shadow_orography.core.calendar import (
    compute_shadow_calendar,
    export_results_csv,
    project_to_dict,
)
from shadow_orography.core.geometry import load_polygon_from_shapefile, shadow_ellipse_polygon
from shadow_orography.core.shadow_model import ProjectParameters, Turbine
from shadow_orography.core.solar import (
    compute_solar_position,
    filter_daylight,
    make_yearly_time_index,
)


class MainWindow(QMainWindow):
    """Main application window."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Shadow Orography Studio")
        self.resize(1200, 800)

        self.aoi_polygon: Polygon | None = None
        self.aoi_path: str | None = None
        self.turbines: list[Turbine] = []
        self.parameters = ProjectParameters(
            latitude=45.0,
            longitude=10.0,
            year=2024,
            min_solar_elevation_deg=5.0,
        )
        self.solar_df = pd.DataFrame()
        self.daylight_df = pd.DataFrame()
        self.current_day_df = pd.DataFrame()
        self.results_df = pd.DataFrame()

        self.scene = QGraphicsScene(self)
        self.view = QGraphicsView(self.scene)

        self.timeline = QSlider(Qt.Orientation.Horizontal)
        self.timeline.valueChanged.connect(self.on_timeline_changed)
        self.time_label = QLabel("No frame")

        self.play_button = QPushButton("Play")
        self.play_button.clicked.connect(self.toggle_play)
        self.speed_combo = QComboBox()
        self.speed_combo.addItems(["1x", "2x", "4x", "8x"])

        self.day_selector = QComboBox()
        self.day_selector.currentTextChanged.connect(self.on_day_changed)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.advance_frame)

        self._build_ui()

    def _build_ui(self) -> None:
        controls = QWidget()
        controls_layout = QVBoxLayout(controls)

        form = QFormLayout()
        self.year_input = QSpinBox()
        self.year_input.setRange(2000, 2100)
        self.year_input.setValue(self.parameters.year)
        form.addRow("Year", self.year_input)

        self.min_elev_input = QSpinBox()
        self.min_elev_input.setRange(0, 45)
        self.min_elev_input.setValue(int(self.parameters.min_solar_elevation_deg))
        form.addRow("Min solar elev (deg)", self.min_elev_input)
        controls_layout.addLayout(form)

        load_aoi_btn = QPushButton("Load AOI shapefile")
        load_aoi_btn.clicked.connect(self.load_aoi)
        controls_layout.addWidget(load_aoi_btn)

        load_project_btn = QPushButton("Load project JSON")
        load_project_btn.clicked.connect(self.load_project)
        controls_layout.addWidget(load_project_btn)

        save_project_btn = QPushButton("Save project JSON")
        save_project_btn.clicked.connect(self.save_project)
        controls_layout.addWidget(save_project_btn)

        add_demo_btn = QPushButton("Add demo turbines")
        add_demo_btn.clicked.connect(self.add_demo_turbines)
        controls_layout.addWidget(add_demo_btn)

        compute_btn = QPushButton("Compute intersections")
        compute_btn.clicked.connect(self.compute)
        controls_layout.addWidget(compute_btn)

        export_csv_btn = QPushButton("Export CSV")
        export_csv_btn.clicked.connect(self.export_csv)
        controls_layout.addWidget(export_csv_btn)

        export_video_btn = QPushButton("Export WebM")
        export_video_btn.clicked.connect(self.export_webm)
        controls_layout.addWidget(export_video_btn)

        controls_layout.addWidget(QLabel("Day"))
        controls_layout.addWidget(self.day_selector)
        controls_layout.addWidget(self.play_button)
        controls_layout.addWidget(QLabel("Speed"))
        controls_layout.addWidget(self.speed_combo)
        controls_layout.addWidget(self.timeline)
        controls_layout.addWidget(self.time_label)
        controls_layout.addStretch()

        central = QWidget()
        layout = QHBoxLayout(central)
        layout.addWidget(controls, 0)
        layout.addWidget(self.view, 1)
        self.setCentralWidget(central)

    def load_aoi(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "AOI shapefile", "", "Shapefile (*.shp)")
        if not path:
            return
        polygon, _ = load_polygon_from_shapefile(path)
        self.aoi_polygon = polygon
        self.aoi_path = path
        self.redraw_scene()

    def add_demo_turbines(self) -> None:
        self.turbines = [
            Turbine("T1", 0.0, 0.0, 120.0, 140.0),
            Turbine("T2", 300.0, 150.0, 100.0, 120.0),
        ]
        self.redraw_scene()

    def _refresh_parameters(self) -> None:
        self.parameters = ProjectParameters(
            latitude=self.parameters.latitude,
            longitude=self.parameters.longitude,
            year=int(self.year_input.value()),
            min_solar_elevation_deg=float(self.min_elev_input.value()),
            timezone="Europe/Rome",
            timestep_minutes=15,
        )

    def compute(self) -> None:
        self._refresh_parameters()
        if self.aoi_polygon is None:
            QMessageBox.warning(self, "Missing AOI", "Load an AOI shapefile first")
            return
        if not self.turbines:
            QMessageBox.warning(self, "Missing turbines", "Add at least one turbine")
            return

        self.results_df = compute_shadow_calendar(self.aoi_polygon, self.turbines, self.parameters)

        times = make_yearly_time_index(
            self.parameters.year,
            self.parameters.timezone,
            self.parameters.timestep_minutes,
        )
        self.solar_df = compute_solar_position(
            times,
            self.parameters.latitude,
            self.parameters.longitude,
        )
        self.daylight_df = filter_daylight(self.solar_df, self.parameters.min_solar_elevation_deg)

        if self.daylight_df.empty:
            return
        days = sorted({ts.strftime("%Y-%m-%d") for ts in self.daylight_df.index})
        self.day_selector.clear()
        self.day_selector.addItems(days)
        self.on_day_changed(days[0])

    def on_day_changed(self, day_text: str) -> None:
        if self.daylight_df.empty or not day_text:
            return
        mask = self.daylight_df.index.strftime("%Y-%m-%d") == day_text
        self.current_day_df = self.daylight_df[mask]
        self.timeline.setMinimum(0)
        self.timeline.setMaximum(max(0, len(self.current_day_df) - 1))
        self.timeline.setValue(0)
        self.redraw_scene()

    def on_timeline_changed(self, frame: int) -> None:
        if self.current_day_df.empty:
            return
        frame = max(0, min(frame, len(self.current_day_df) - 1))
        timestamp = self.current_day_df.index[frame]
        self.time_label.setText(timestamp.isoformat())
        self.redraw_scene(frame)

    def toggle_play(self) -> None:
        if self.timer.isActive():
            self.timer.stop()
            self.play_button.setText("Play")
            return
        speed = int(self.speed_combo.currentText().replace("x", ""))
        interval = max(20, int(350 / speed))
        self.timer.start(interval)
        self.play_button.setText("Pause")

    def advance_frame(self) -> None:
        if self.current_day_df.empty:
            return
        value = self.timeline.value() + 1
        if value > self.timeline.maximum():
            value = 0
        self.timeline.setValue(value)

    def _scene_bounds(self) -> tuple[float, float, float, float]:
        if self.aoi_polygon is not None:
            minx, miny, maxx, maxy = self.aoi_polygon.bounds
            return minx - 100.0, miny - 100.0, maxx + 100.0, maxy + 100.0
        return -500.0, -500.0, 500.0, 500.0

    def redraw_scene(self, frame: int = 0) -> None:
        self.scene.clear()
        minx, miny, maxx, maxy = self._scene_bounds()
        self.scene.setSceneRect(minx, -maxy, maxx - minx, maxy - miny)

        if self.aoi_polygon is not None:
            pts = [
                (x, -y)
                for x, y in self.aoi_polygon.exterior.coords
            ]
            poly = QPolygonF([*map(lambda p: self._qp(*p), pts)])
            aoi_item = QGraphicsPolygonItem(poly)
            aoi_item.setPen(QPen(Qt.GlobalColor.darkGreen, 2))
            self.scene.addItem(aoi_item)

        for turbine in self.turbines:
            item = QGraphicsEllipseItem(turbine.x - 4, -turbine.y - 4, 8, 8)
            item.setPen(QPen(Qt.GlobalColor.red, 1))
            item.setBrush(Qt.GlobalColor.red)
            self.scene.addItem(item)

        if self.current_day_df.empty:
            return

        frame = max(0, min(frame, len(self.current_day_df) - 1))
        rows = self.current_day_df.iloc[: frame + 1]

        for turbine in self.turbines:
            traj = []
            for _, row in rows.iterrows():
                ellipse = shadow_ellipse_polygon(
                    turbine.x,
                    turbine.y,
                    turbine.hub_height_m,
                    turbine.rotor_radius_m,
                    float(row["azimuth"]),
                    float(row["apparent_elevation"]),
                )
                cx, cy = ellipse.centroid.x, ellipse.centroid.y
                traj.append((cx, -cy))

            if traj:
                polyline = QPolygonF([self._qp(x, y) for x, y in traj])
                trajectory_item = QGraphicsPolygonItem(polyline)
                trajectory_item.setPen(QPen(Qt.GlobalColor.darkCyan, 1))
                self.scene.addItem(trajectory_item)

                ellipse = shadow_ellipse_polygon(
                    turbine.x,
                    turbine.y,
                    turbine.hub_height_m,
                    turbine.rotor_radius_m,
                    float(rows.iloc[-1]["azimuth"]),
                    float(rows.iloc[-1]["apparent_elevation"]),
                )
                pts = [(x, -y) for x, y in ellipse.exterior.coords]
                poly = QPolygonF([self._qp(x, y) for x, y in pts])
                shadow_item = QGraphicsPolygonItem(poly)
                shadow_item.setPen(QPen(Qt.GlobalColor.blue, 1))
                self.scene.addItem(shadow_item)

    def export_csv(self) -> None:
        if self.results_df.empty:
            QMessageBox.information(self, "No results", "Run computation first")
            return
        path, _ = QFileDialog.getSaveFileName(self, "Export CSV", "results.csv", "CSV (*.csv)")
        if not path:
            return
        export_results_csv(self.results_df, path)

    def export_webm(self) -> None:
        if self.current_day_df.empty:
            QMessageBox.information(self, "No animation", "Compute and pick a day first")
            return
        if importlib.util.find_spec("imageio") is None:
            QMessageBox.critical(
                self,
                "Missing dependency",
                "The optional dependency 'imageio' is not available. "
                "Install it and rebuild the executable to enable WebM export.",
            )
            return
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Export WebM",
            "animation.webm",
            "WebM (*.webm)",
        )
        if not path:
            return

        frames: list[np.ndarray] = []
        for idx in range(len(self.current_day_df)):
            self.redraw_scene(idx)
            image = QImage(self.view.viewport().size(), QImage.Format.Format_ARGB32)
            image.fill(Qt.GlobalColor.white)
            painter = QPainter(image)
            self.view.render(painter)
            painter.end()
            ptr = image.bits()
            arr = np.array(ptr).reshape(image.height(), image.width(), 4)
            frames.append(arr[:, :, :3].copy())

        iio = importlib.import_module("imageio.v3")
        iio.imwrite(path, np.stack(frames), fps=10)

    def save_project(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "Save Project", "project.json", "JSON (*.json)")
        if not path:
            return
        payload = project_to_dict(
            turbines=self.turbines,
            aoi_path=self.aoi_path or "",
            parameters=self.parameters,
            results_path=None,
        )
        Path(path).write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def load_project(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Load Project", "", "JSON (*.json)")
        if not path:
            return
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        self.turbines = [Turbine(**item) for item in payload.get("turbines", [])]
        aoi_path = payload.get("aoi_path")
        if aoi_path:
            polygon, _ = load_polygon_from_shapefile(aoi_path)
            self.aoi_polygon = polygon
            self.aoi_path = aoi_path
        params = payload.get("parameters", {})
        if params:
            self.parameters = ProjectParameters(**params)
            self.year_input.setValue(self.parameters.year)
            self.min_elev_input.setValue(int(self.parameters.min_solar_elevation_deg))
        self.redraw_scene()

    @staticmethod
    def _qp(x: float, y: float):
        from PySide6.QtCore import QPointF

        return QPointF(x, y)


def run() -> None:
    """Start the Qt application."""
    log_path = Path(tempfile.gettempdir()) / "shadow_orography_startup.log"

    def log_exception(exc_type, exc_value, exc_tb) -> None:
        with log_path.open("a", encoding="utf-8") as handle:
            handle.write(f"\n[{datetime.now().astimezone().isoformat()}] Unhandled exception\n")
            traceback.print_exception(exc_type, exc_value, exc_tb, file=handle)

    sys.excepthook = log_exception

    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(f"\n[{datetime.now().astimezone().isoformat()}] App startup\n")

    app = QApplication([])
    window = MainWindow()
    window.show()
    app.exec()
