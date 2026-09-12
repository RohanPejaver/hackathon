"""Field scripts run as a person would run them (subprocess, cwd = repo root) against
synthetic frames from `synth.py`. Nothing here touches the real config tree or `data/`."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import cv2
import pytest
import yaml

from tests.perception.synth import mm_to_px, render_frame

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"


def run(script: str, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPTS / script), *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


@pytest.fixture
def config_copy(tmp_path: Path) -> Path:
    dst = tmp_path / "config"
    shutil.copytree(ROOT / "config", dst)
    return dst


@pytest.fixture
def frame_file(tmp_path: Path) -> Path:
    path = tmp_path / "frame.png"
    cv2.imwrite(str(path), render_frame(glove_px=mm_to_px((170.0, 470.0))))
    return path


def _decode(path: Path) -> list[int]:
    d = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
    detector = cv2.aruco.ArucoDetector(d, cv2.aruco.DetectorParameters())
    _corners, ids, _ = detector.detectMarkers(cv2.imread(str(path)))
    return [] if ids is None else [int(i) for i in ids.ravel()]


def test_print_markers_writes_decodable_pngs(tmp_path: Path) -> None:
    out = tmp_path / "markers"
    result = run("print_markers.py", "--out", str(out), "--dpi", "150")
    assert result.returncode == 0, result.stderr
    expected = {
        "corner_00.png": 0,
        "corner_01.png": 1,
        "corner_02.png": 2,
        "corner_03.png": 3,
        "tool_10_spreader.png": 10,
        "tool_11_spreader_2.png": 11,
        "tool_12_spreader_3.png": 12,
        "surface_20_board.png": 20,
        "surface_21_board_2.png": 21,
    }
    for name, marker_id in expected.items():
        assert (out / name).is_file(), name
        assert _decode(out / name) == [marker_id], name
    sheet = (out / "SHEET.md").read_text()
    assert "front-left" in sheet and "100% scale" in sheet and "matte" in sheet
    # 80 mm at 150 dpi = 472 px marker plus quiet zones: physically sized
    h, w = cv2.imread(str(out / "corner_00.png")).shape[:2]
    assert w >= 472 and h > w
    before = (out / "corner_00.png").read_bytes()
    assert run("print_markers.py", "--out", str(out), "--dpi", "150").returncode == 0
    assert (out / "corner_00.png").read_bytes() == before, "idempotent"


def test_calibrate_dry_run_reports_error_and_writes_nothing(
    config_copy: Path, frame_file: Path
) -> None:
    station = config_copy / "station" / "demo.yaml"
    before = station.read_bytes()
    result = run("calibrate.py", "--frame-file", str(frame_file), "--config-root", str(config_copy))
    assert result.returncode == 0, result.stderr
    m = re.search(r"reprojection error: ([0-9.]+) mm", result.stdout)
    assert m is not None, result.stdout
    assert float(m.group(1)) < 2.0
    assert "dry run" in result.stdout
    assert station.read_bytes() == before


def test_calibrate_write_bumps_version_and_stores_homography(
    config_copy: Path, frame_file: Path
) -> None:
    station = config_copy / "station" / "demo.yaml"
    result = run(
        "calibrate.py",
        "--frame-file",
        str(frame_file),
        "--config-root",
        str(config_copy),
        "--write",
    )
    assert result.returncode == 0, result.stderr
    data = yaml.safe_load(station.read_text())
    assert data["config_version"] == 2
    H = data["calibration"]["homography"]
    assert len(H) == 3 and all(len(row) == 3 for row in H)
    assert all(isinstance(v, float) for row in H for v in row)
    assert "config checksum:" in result.stdout
    # the written file still loads through the real loader (the script prints its checksum)
    assert data["zones"][0]["zone_id"] == "bin:pesto"


def test_calibrate_refuses_without_corners(config_copy: Path, tmp_path: Path) -> None:
    blank = tmp_path / "blank.png"
    cv2.imwrite(str(blank), render_frame(corners_px={}))
    result = run(
        "calibrate.py", "--frame-file", str(blank), "--config-root", str(config_copy), "--write"
    )
    assert result.returncode == 1
    assert (
        yaml.safe_load((config_copy / "station" / "demo.yaml").read_text())["config_version"] == 1
    )


def test_tune_hsv_headless_prints_blob_area(config_copy: Path, frame_file: Path) -> None:
    result = run(
        "tune_hsv.py",
        "--headless",
        "--frame-file",
        str(frame_file),
        "--config-root",
        str(config_copy),
    )
    assert result.returncode == 0, result.stderr
    m = re.search(r"blob area \(configured\): (\d+) px", result.stdout)
    assert m is not None, result.stdout
    assert int(m.group(1)) > 1500
    assert "hue -10" in result.stdout and "sat +20" in result.stdout
    defaults_before = (config_copy / "defaults.yaml").read_bytes()
    assert (config_copy / "defaults.yaml").read_bytes() == defaults_before


def test_tune_hsv_headless_write_updates_defaults(config_copy: Path, frame_file: Path) -> None:
    result = run(
        "tune_hsv.py",
        "--headless",
        "--frame-file",
        str(frame_file),
        "--config-root",
        str(config_copy),
        "--write",
        "--lower",
        "90,70,50",
        "--upper",
        "150,255,255",
    )
    assert result.returncode == 0, result.stderr
    data = yaml.safe_load((config_copy / "defaults.yaml").read_text())
    assert data["perception"]["gloves"]["hsv_lower"] == [90, 70, 50]
    assert data["perception"]["gloves"]["hsv_upper"] == [150, 255, 255]


def test_eval_perception_synthetic_passes(tmp_path: Path) -> None:
    result = run(
        "eval_perception.py", "--synthetic", "--out-dir", str(tmp_path), "--date", "2026-01-01"
    )
    report_path = tmp_path / "2026-01-01" / "p4_perception_report.json"
    assert report_path.is_file(), result.stdout + result.stderr
    report = json.loads(report_path.read_text())
    for key in (
        "phase",
        "date",
        "clips",
        "aggregate",
        "occlusion_recall",
        "nuisance_rate_per_hour",
        "normal_minutes",
        "targets",
        "passed",
        "notes",
        "synthetic",
    ):
        assert key in report, key
    assert report["phase"] == "P4" and report["synthetic"] is True
    assert set(report["clips"]) == {"synthetic-zone-occlusion", "synthetic-contact"}
    by_type = report["aggregate"]["by_type"]
    assert set(by_type) == {"ZONE_ENTRY", "ZONE_EXIT", "CONTACT_BEGIN", "CONTACT_END"}
    assert report["occlusion_recall"] == 1.0
    assert report["nuisance_rate_per_hour"] == 0.0 and report["normal_minutes"] > 0
    assert report["passed"] is True, report["failures"]
    assert result.returncode == 0, result.stdout + result.stderr
    assert any("T-nuisance" in n for n in report["notes"])


def test_eval_perception_without_clips_exits_one(tmp_path: Path) -> None:
    result = run(
        "eval_perception.py",
        "--videos",
        str(tmp_path / "none"),
        "--normal",
        str(tmp_path / "none"),
        "--out-dir",
        str(tmp_path),
    )
    assert result.returncode == 1
    assert "record_fixture.py" in result.stderr
