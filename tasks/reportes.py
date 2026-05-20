from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from app import create_app
from services.reportes import EXPORT_MIMETYPES, build_report_export_file
from utils.tenant import tenant_context


def export_report_job(
    report_type: str,
    formato: str,
    filtros: dict[str, Any],
    clinica_id: int,
    user_label: str,
) -> dict[str, Any]:
    app = create_app()
    with app.app_context(), tenant_context(clinica_id):
        file_path = build_report_export_file(report_type, formato, filtros or {}, user_label, clinica_id)
        return {
            "tipo": report_type,
            "formato": formato,
            "clinica_id": int(clinica_id),
            "file_path": str(Path(file_path).resolve()),
            "download_name": os.path.basename(file_path),
            "mimetype": EXPORT_MIMETYPES.get(formato, "application/octet-stream"),
        }
