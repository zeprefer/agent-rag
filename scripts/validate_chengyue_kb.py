from __future__ import annotations

import hashlib
import json
import statistics
import sys
import types
from pathlib import Path
from types import SimpleNamespace


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

# The standalone artifact runtime intentionally does not load the full API
# dependency set. Provide only the parser/chunker settings used by this check.
config_stub = types.ModuleType("app.core.config")
config_stub.settings = SimpleNamespace(
    chunk_target_tokens=700,
    chunk_overlap_tokens=120,
    security_scan_enabled=True,
    libreoffice_binary="soffice",
)
sys.modules["app.core.config"] = config_stub

from app.services.chunking import build_chunks  # noqa: E402
from app.services.document_parsers import parse_document_bytes  # noqa: E402
from app.services.security_scan import scan_upload  # noqa: E402


PACK = ROOT / "sample_data" / "chengyue_enterprise_kb"
KB_DIR = PACK / "knowledge_base_files"
REPORT_PATH = PACK / "_test_guide" / "validation_report.json"
ALLOWED = {"md", "docx", "pdf"}
EXPECTED = {
    "01_company_operating_model.md": ["CN-SZ", "CN-SHEN", "CY-CS-2026-027"],
    "02_employee_handbook_2026.md": ["HR-REMOTE-03", "每周最多 2 个远程工作日", "家庭照护假"],
    "03_information_security_and_data_classification.md": ["L4 严格受限", "7711", "BCP-RTO-042"],
    "04_product_service_catalog.md": ["CYX7-4200", "36 个月", "HW-ADV-RPL"],
    "05_travel_and_expense_policy.docx": ["FIN-EX-09", "A 类城市 220 元", "深圳为 A 类"],
    "06_procurement_and_supplier_management.md": ["三份可比报价", "300,000 元", "1 个工作日内撤销"],
    "07_customer_success_and_escalation_playbook.md": ["ORION-27", "Conditional Go", "红色商务风险"],
    "08_incident_postmortem_atlasops_2026_02_18.md": ["max.batch.records", "5,000", "差异为零"],
    "09_change_release_and_rollback_sop.md": ["策略上限为 1,200", "标准值为 800", "go/no-go"],
    "10_customer_support_sla_v2.2.pdf": ["10 分钟", "4 小时", "99.5%"],
}


def main():
    failures = []
    documents = []
    for path in sorted(KB_DIR.iterdir()):
        if not path.is_file():
            continue
        ext = path.suffix.lower().lstrip(".")
        if ext not in ALLOWED:
            failures.append(f"unsupported file in upload folder: {path.name}")
            continue
        data = path.read_bytes()
        scan_upload(filename=path.name, extension=ext, data=data)
        sections = parse_document_bytes(file_type=ext, filename=path.name, data=data)
        chunks = build_chunks(sections)
        combined = "\n".join(
            "\n".join(part for part in (section.heading_path, section.text) if part)
            for section in sections
        )
        missing = [phrase for phrase in EXPECTED.get(path.name, []) if phrase not in combined]
        if missing:
            failures.append(f"{path.name}: missing extracted phrases {missing}")
        if not chunks:
            failures.append(f"{path.name}: produced no chunks")
        token_counts = [chunk.token_count for chunk in chunks]
        documents.append({
            "filename": path.name,
            "extension": ext,
            "bytes": len(data),
            "sha256": hashlib.sha256(data).hexdigest(),
            "sections": len(sections),
            "chunks": len(chunks),
            "extracted_characters": len(combined),
            "heading_sections": sum(section.heading_path is not None for section in sections),
            "page_sections": sum(section.page_number is not None for section in sections),
            "chunk_tokens": {
                "min": min(token_counts),
                "max": max(token_counts),
                "mean": round(statistics.mean(token_counts), 1),
            },
        })

    test_cases = []
    for line_number, line in enumerate((PACK / "_test_guide" / "test_cases.jsonl").read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        case = json.loads(line)
        for source in case.get("sources", []):
            if not (KB_DIR / source).exists() and not (PACK / "version_seed" / source).exists():
                failures.append(f"test case {case['id']} refers to missing source {source}")
        test_cases.append(case["id"])

    report = {
        "status": "passed" if not failures else "failed",
        "knowledge_base_directory": str(KB_DIR),
        "document_count": len(documents),
        "total_bytes": sum(document["bytes"] for document in documents),
        "total_extracted_characters": sum(document["extracted_characters"] for document in documents),
        "total_chunks": sum(document["chunks"] for document in documents),
        "documents": documents,
        "test_case_count": len(test_cases),
        "failures": failures,
    }
    REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
