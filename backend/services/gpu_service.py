"""GPU telemetry service backed by nvidia-smi."""

from __future__ import annotations

import logging
import re
import subprocess

from backend.models.system import GPUStatusResponse
from goat_ai.config import Settings

logger = logging.getLogger(__name__)

_GPU_MODEL_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\bRTX\s*([A-Z]?\d{3,4}[A-Z0-9]*)\b", re.IGNORECASE),
    re.compile(r"\b([ABHLTV]\d{1,4}[A-Z0-9]*)\b", re.IGNORECASE),
)

_GPU_NAME_NOISE = (
    "NVIDIA",
    "GEFORCE",
    "TESLA",
    "QUADRO",
    "GRAPHICS",
    "GPU",
)


def _normalize_gpu_name(raw_name: str) -> str:
    """Reduce nvidia-smi model strings to a short, user-facing GPU name."""
    text = " ".join(raw_name.strip().split())
    if not text:
        return "GPU"

    for pattern in _GPU_MODEL_PATTERNS:
        match = pattern.search(text)
        if match:
            prefix = "RTX" if pattern.pattern.startswith(r"\bRTX") else ""
            return f"{prefix}{match.group(1).replace(' ', '')}"

    cleaned = text
    for token in _GPU_NAME_NOISE:
        cleaned = re.sub(rf"\b{re.escape(token)}\b", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(
        r"\b(SXM\d+|PCIe|HBM\d+|SUPER|TI|LHR|MIG)\b", "", cleaned, flags=re.IGNORECASE
    )
    cleaned = re.sub(r"[\s\-/_,()]+", " ", cleaned).strip()
    if not cleaned:
        return text
    return " ".join(cleaned.split()[:2])


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
    gpu_name = _normalize_gpu_name(parts[0])
    return GPUStatusResponse(
        available=True,
        active=True,
        message=f"{gpu_name}: Active",
        name=gpu_name,
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
