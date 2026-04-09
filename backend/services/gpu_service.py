"""GPU telemetry service backed by nvidia-smi."""

from __future__ import annotations

import logging
import subprocess

from backend.models.system import GPUStatusResponse
from goat_ai.config import Settings

logger = logging.getLogger(__name__)


def _parse_float(value: str) -> float | None:
    """Parse numeric CSV fields from nvidia-smi output."""
    text = value.strip()
    if not text or text == "[N/A]":
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _parse_gpu_row(line: str) -> GPUStatusResponse:
    """Parse one nvidia-smi CSV row into API response shape."""
    parts = [p.strip() for p in line.split(",")]
    if len(parts) < 7:
        return GPUStatusResponse(
            available=False, active=False, message="GPU telemetry parse error"
        )
    utilization = _parse_float(parts[2]) or 0.0
    return GPUStatusResponse(
        available=True,
        active=True,
        message="A100 Inference Engine: Active",
        name=parts[0],
        uuid=parts[1],
        utilization_gpu=utilization,
        memory_used_mb=_parse_float(parts[3]),
        memory_total_mb=_parse_float(parts[4]),
        temperature_c=_parse_float(parts[5]),
        power_draw_w=_parse_float(parts[6]),
    )


def read_gpu_status(settings: Settings) -> GPUStatusResponse:
    """Read one GPU's telemetry; never raises."""
    try:
        target = settings.gpu_target_uuid or str(settings.gpu_target_index)
        result = subprocess.run(
            [
                "nvidia-smi",
                f"--id={target}",
                "--query-gpu=name,uuid,utilization.gpu,memory.used,memory.total,temperature.gpu,power.draw",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True,
            text=True,
            timeout=2,
            check=False,
        )
    except FileNotFoundError:
        return GPUStatusResponse(
            available=False,
            active=False,
            message="Telemetry unavailable: nvidia-smi not found",
        )
    except subprocess.TimeoutExpired:
        return GPUStatusResponse(
            available=False,
            active=False,
            message="Telemetry unavailable: nvidia-smi timeout",
        )
    except Exception:
        logger.exception("Unexpected GPU telemetry error")
        return GPUStatusResponse(
            available=False,
            active=False,
            message="Telemetry unavailable",
        )

    if result.returncode != 0:
        logger.warning(
            "nvidia-smi failed (%s): %s", result.returncode, result.stderr.strip()
        )
        return GPUStatusResponse(
            available=False,
            active=False,
            message="Telemetry unavailable",
        )

    first_line = next(
        (ln.strip() for ln in result.stdout.splitlines() if ln.strip()), ""
    )
    if not first_line:
        return GPUStatusResponse(
            available=False,
            active=False,
            message="Telemetry unavailable",
        )
    return _parse_gpu_row(first_line)
