"""Mock routes for UI development without DB/VLM.

Activated by setting MOCK_DATA=true in .env. Provides the same page and API
routes as the real app but returns hardcoded demo data. The real routers
are not loaded in mock mode.
"""

from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

router = APIRouter()
templates = Jinja2Templates(
    directory=Path(__file__).resolve().parent.parent / "templates"
)

_MOCK_USER = SimpleNamespace(
    employee_name="Demo User", sub="demo", jwt_scopes=["read", "write", "admin"]
)


def _ctx(request: Request, **extra) -> dict:
    return {
        "request": request,
        "user": _MOCK_USER,
        "scopes": _MOCK_USER.jwt_scopes,
        **extra,
    }


# ═══════════════════════════════════════════════
# API endpoints (JSON)
# ═══════════════════════════════════════════════

@router.get("/api/cases")
async def api_cases(
    q: str | None = None,
    customer: str | None = None,
    device: str | None = None,
    year: int | None = None,
    week: int | None = None,
    page: int = 1,
):
    items = []
    for i in range(1, 9):
        items.append({
            "id": i,
            "date": f"2026-03-{10 + i:02d}",
            "customer": ["Customer A", "Customer B", "Customer C", "Customer D"][
                i % 4
            ],
            "device": ["DDR5-4800", "LPDDR5-6400", "DDR4-3200", "HBM3"][i % 4],
            "model": f"K4A8G{160 + i}WC",
            "defect_mode": ["Bit Fail", "Open/Short", "Retention Fail", "Row Hammer"][
                i % 4
            ],
            "defect_rate_raw": f"{0.05 + i * 0.03:.2f}%",
            "fab_assembly": f"FAB-{'ABCD'[i % 4]}",
            "fa_status": [
                "Root cause identified",
                "Under analysis",
                "Corrective action",
                "Closed",
            ][i % 4],
            "follow_up": [
                "Monitor next lot",
                "Waiting vendor feedback",
                "Retest scheduled",
                "No action needed",
            ][i % 4],
            "updated_at": "2026-03-20T14:30:00",
        })
    return {"items": items, "total": len(items), "page": 1}


@router.get("/api/upload/{report_id}/results")
async def api_upload_results(report_id: int):
    slides = []
    for i in range(1, 7):
        slide: dict = {
            "slide_number": i + 2,
            "image_path": f"reports/1/slides/slide_{i + 2:03d}.png",
            "raw_vlm_response": None,
        }
        if i == 4:
            slide["data"] = None
            slide["error"] = "VLM extraction timeout"
        else:
            slide["data"] = {
                "date": f"2026-03-{10 + i:02d}",
                "customer": ["Customer A", "Customer B", "Customer C"][i % 3],
                "device": ["DDR5-4800", "LPDDR5-6400", "DDR4-3200"][i % 3],
                "model": f"K4A8G{160 + i}WC-BCWE",
                "defect_mode": ["Bit Fail", "Open/Short", "Retention Fail"][i % 3],
                "defect_rate_raw": f"{0.05 + i * 0.02:.2f}%",
                "defect_lots": [f"LOT{i:03d}", f"LOT{i + 10:03d}"],
                "fab_assembly": f"FAB-{'ABC'[i % 3]}",
                "fa_status": [
                    "Root cause identified",
                    "Under analysis",
                    "Corrective action",
                ][i % 3],
                "follow_up": [
                    "Monitor next lot",
                    "Waiting vendor feedback",
                    "Retest scheduled",
                ][i % 3],
            }
        slides.append(slide)
    return {"slides": slides}


# ═══════════════════════════════════════════════
# Page routes (HTML)
# ═══════════════════════════════════════════════

@router.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("home.html", _ctx(request))


@router.get("/upload", response_class=HTMLResponse)
async def upload(request: Request):
    return templates.TemplateResponse("upload.html", _ctx(request))


@router.get("/weeks", response_class=HTMLResponse)
async def weeks_list(request: Request):
    weeks = []
    for i in range(6, 0, -1):
        weeks.append(
            SimpleNamespace(
                period=SimpleNamespace(
                    id=i,
                    year=2026,
                    week_number=10 + i,
                    start_date=f"2026-03-{10 + i * 7:02d}",
                    end_date=f"2026-03-{16 + i * 7:02d}",
                ),
                report_count=2 if i % 2 == 0 else 1,
                case_count=5 + i,
            )
        )
    return templates.TemplateResponse("weeks_list.html", _ctx(request, weeks=weeks))


@router.get("/weeks/{period_id}", response_class=HTMLResponse)
async def week_detail(request: Request, period_id: int):
    period = SimpleNamespace(
        id=period_id,
        year=2026,
        week_number=12,
        start_date="2026-03-16",
        end_date="2026-03-22",
        summary=(
            "本周共處理 8 個 FA 案例，主要集中在 DRAM 良率偏低問題。\n\n"
            "重點：\n"
            "- Customer A 的 DDR5 device 出現新的 defect mode\n"
            "- Customer B 案例已完成 root cause 分析"
        ),
    )
    reports = []
    for status in ["done", "review", "triage"]:
        reports.append(
            SimpleNamespace(
                report=SimpleNamespace(
                    id=len(reports) + 1,
                    filename=f"FA_Weekly_{status}.pptx",
                    total_slides=25,
                    status=status,
                    created_at=datetime(2026, 3, 20, 14, 30),
                ),
                uploader_name="Demo User",
            )
        )
    return templates.TemplateResponse(
        "week_detail.html", _ctx(request, period=period, reports=reports)
    )


@router.get("/reports/{report_id}/triage", response_class=HTMLResponse)
async def triage(request: Request, report_id: int):
    report = SimpleNamespace(
        id=report_id,
        filename="FA_Weekly_Report_2026W12.pptx",
        weekly_period_id=1,
    )
    slides = []
    for i in range(1, 13):
        slide: dict = {
            "id": i,
            "slide_number": i,
            "image_path": f"reports/1/slides/slide_{i:03d}.png",
            "is_candidate": i <= 8,
            "classification_status": "case" if i % 3 != 0 else "not_case",
            "classification_confidence": 0.92 if i % 3 != 0 else 0.85,
            "linked_case_id": None,
        }
        if i == 7:
            slide["classification_status"] = "error"
            slide["classification_confidence"] = None
        if i == 5:
            slide["classification_confidence"] = 0.55
        slides.append(slide)

    return templates.TemplateResponse(
        "triage.html", _ctx(request, report=report, slides_json=slides)
    )


@router.get("/reports/{report_id}/review", response_class=HTMLResponse)
async def review(request: Request, report_id: int):
    report = SimpleNamespace(
        id=report_id,
        filename="FA_Weekly_Report_2026W12.pptx",
        weekly_period_id=1,
    )
    return templates.TemplateResponse("review.html", _ctx(request, report=report))


@router.get("/reports/{report_id}/slides", response_class=HTMLResponse)
async def report_slides(request: Request, report_id: int):
    report = SimpleNamespace(
        id=report_id,
        filename="FA_Weekly_Report_2026W12.pptx",
        weekly_period_id=1,
        status="done",
    )
    slides = []
    for i in range(1, 13):
        slides.append(
            SimpleNamespace(
                id=i,
                slide_number=i,
                image_path=f"reports/{report_id}/slides/slide_{i:03d}.png",
                is_candidate=i <= 8,
                linked_case_id=i if i <= 4 else None,
            )
        )
    return templates.TemplateResponse(
        "report_slides.html", _ctx(request, report=report, slides=slides)
    )


@router.get("/cases", response_class=HTMLResponse)
async def case_list(request: Request):
    return templates.TemplateResponse("case_list.html", _ctx(request))


@router.get("/cases/{case_id}", response_class=HTMLResponse)
async def case_detail(request: Request, case_id: int):
    case = SimpleNamespace(
        id=case_id,
        slide_number=5,
        slide_image_path="reports/1/slides/slide_005.png",
        date="2026-03-18",
        customer="Customer A",
        device="DDR5-4800",
        model="K4A8G165WC-BCWE",
        defect_mode="Bit Fail",
        defect_rate_raw="0.15%",
        defect_lots=["LOT001", "LOT002", "LOT003"],
        fab_assembly="FAB-A",
        fa_status="Root cause identified",
        follow_up="Corrective action in progress",
    )
    return templates.TemplateResponse("case_detail.html", _ctx(request, case=case))
