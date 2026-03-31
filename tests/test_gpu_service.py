from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from backend.services.gpu_service import _parse_gpu_row, read_gpu_status
from goat_ai.config import Settings


class GPUServiceTests(unittest.TestCase):
    def _settings(self) -> Settings:
        tmp = Path(tempfile.gettempdir())
        return Settings(
            ollama_base_url="http://127.0.0.1:11434",
            generate_timeout=120,
            max_upload_mb=20,
            max_upload_bytes=20 * 1024 * 1024,
            max_dataframe_rows=50000,
            use_chat_api=True,
            system_prompt="test",
            app_root=tmp,
            logo_svg=tmp / "logo.svg",
            log_db_path=tmp / "chat_logs.db",
            gpu_target_uuid="",
            gpu_target_index=0,
        )

    def test_parse_gpu_row_happy_path(self) -> None:
        row = "NVIDIA A100-SXM4-80GB, GPU-abc, 42, 1000, 81920, 35, 80.5"
        parsed = _parse_gpu_row(row)
        self.assertTrue(parsed.available)
        self.assertEqual("NVIDIA A100-SXM4-80GB", parsed.name)
        self.assertEqual(42.0, parsed.utilization_gpu)
        self.assertEqual(1000.0, parsed.memory_used_mb)

    def test_read_gpu_status_when_smi_missing(self) -> None:
        with patch("backend.services.gpu_service.subprocess.run", side_effect=FileNotFoundError):
            status = read_gpu_status(self._settings())
        self.assertFalse(status.available)
        self.assertIn("nvidia-smi", status.message)


if __name__ == "__main__":
    unittest.main()
