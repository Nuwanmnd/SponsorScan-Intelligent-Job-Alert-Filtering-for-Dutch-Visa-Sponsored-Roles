import sys
import os
from typing import Any, List, Optional
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session
import datetime

# Add parent directory to path to import database.py and main.py
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database import SessionLocal, Job, engine, Base
from main import run_collection
from backend.ai_service import AIServiceError, analyze_job, tailor_application

# Pydantic Models
class JobSchema(BaseModel):
    id: int
    title: str
    company: str
    link: Optional[str] = None
    date_found: datetime.date
    status: str
    email_id: Optional[str] = None

    class Config:
        orm_mode = True

class JobUpdate(BaseModel):
    status: str


class JobDescriptionRequest(BaseModel):
    job_description: str


class AnalyzeJobResponse(BaseModel):
    fit_score: int
    fit_summary: str
    match_reasons: List[str]
    concerns: List[str]
    legitimacy_assessment: str
    seriousness_assessment: str
    recommendation: str
    next_step: str
    raw_response: Optional[str] = None


class SectionDecisionNotes(BaseModel):
    keep: List[str]
    remove: List[str]
    rewrite: List[str]


class TailorSectionNotes(BaseModel):
    skills: SectionDecisionNotes
    projects: SectionDecisionNotes
    experience: SectionDecisionNotes
    education: SectionDecisionNotes
    general_structure: SectionDecisionNotes


class FinalOnePageCVDraft(BaseModel):
    title: str
    profile_summary: str
    skills: List[str]
    experience: List[str]
    projects: List[str]
    education: List[str]
    additional_sections: List[str]


class TailorApplicationResponse(BaseModel):
    recommended_cv_title: str
    recommended_profile_summary: str
    section_notes: TailorSectionNotes
    final_one_page_cv_draft: FinalOnePageCVDraft
    optional_extra_details: List[str]
    what_not_to_claim: List[str]
    cover_letter: str
    key_points_to_highlight: List[str]
    raw_response: Optional[str] = None

# FastAPI Setup
app = FastAPI(title="Gmail Job Alert API")

# CORS (Allow frontend)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Allow all for local dev
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/")
def read_root():
    return {"message": "Job Alert API is running"}

@app.get("/jobs", response_model=List[JobSchema])
def get_jobs(status: Optional[str] = None, skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """Fetch jobs, optional filtering by status (pending, applied, rejected, approved)."""
    query = db.query(Job)
    if status:
        query = query.filter(Job.status == status)

    jobs = query.order_by(Job.date_found.desc(), Job.id.desc()).offset(skip).limit(limit).all()
    return jobs

@app.post("/jobs/refresh")
def refresh_jobs():
    """Trigger the Gmail collection script."""
    try:
        run_collection()
        return {"message": "Collection complete"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/jobs/{job_id}", response_model=JobSchema)
def update_job_status(job_id: int, update: JobUpdate, db: Session = Depends(get_db)):
    """Update the status of a job."""
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    valid_statuses = ["pending", "applied", "rejected", "approved", "ignored"]
    if update.status not in valid_statuses:
         raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of {valid_statuses}")

    job.status = update.status
    db.commit()
    db.refresh(job)
    return job


def _require_list(value: Any, field_name: str) -> List[str]:
    if not isinstance(value, list):
        raise HTTPException(status_code=502, detail=f"Invalid Claude response for `{field_name}`.")
    return [str(item).strip() for item in value if str(item).strip()]


def _require_dict(value: Any, field_name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise HTTPException(status_code=502, detail=f"Invalid Claude response for `{field_name}`.")
    return value


def _build_section_decision_notes(section_notes: dict[str, Any], field_name: str) -> SectionDecisionNotes:
    return SectionDecisionNotes(
        keep=_require_list(section_notes.get("keep", []), f"{field_name}.keep"),
        remove=_require_list(section_notes.get("remove", []), f"{field_name}.remove"),
        rewrite=_require_list(section_notes.get("rewrite", []), f"{field_name}.rewrite"),
    )


@app.post("/ai/analyze", response_model=AnalyzeJobResponse)
def analyze_job_description(request: JobDescriptionRequest):
    try:
        result = analyze_job(request.job_description)
    except AIServiceError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    try:
        return AnalyzeJobResponse(
            fit_score=int(result["fit_score"]),
            fit_summary=str(result["fit_summary"]).strip(),
            match_reasons=_require_list(result.get("match_reasons", []), "match_reasons"),
            concerns=_require_list(result.get("concerns", []), "concerns"),
            legitimacy_assessment=str(result["legitimacy_assessment"]).strip(),
            seriousness_assessment=str(result["seriousness_assessment"]).strip(),
            recommendation=str(result["recommendation"]).strip(),
            next_step=str(result["next_step"]).strip(),
            raw_response=result.get("_raw_response"),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(status_code=502, detail="Claude returned an unexpected analysis format.") from exc


@app.post("/ai/tailor", response_model=TailorApplicationResponse)
def tailor_job_application(request: JobDescriptionRequest):
    try:
        result = tailor_application(request.job_description)
    except AIServiceError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    try:
        section_notes = _require_dict(result.get("section_notes", {}), "section_notes")
        final_cv_draft = _require_dict(result.get("final_one_page_cv_draft", {}), "final_one_page_cv_draft")
        return TailorApplicationResponse(
            recommended_cv_title=str(result["recommended_cv_title"]).strip(),
            recommended_profile_summary=str(result["recommended_profile_summary"]).strip(),
            section_notes=TailorSectionNotes(
                skills=_build_section_decision_notes(
                    _require_dict(section_notes.get("skills", {}), "section_notes.skills"),
                    "section_notes.skills",
                ),
                projects=_build_section_decision_notes(
                    _require_dict(section_notes.get("projects", {}), "section_notes.projects"),
                    "section_notes.projects",
                ),
                experience=_build_section_decision_notes(
                    _require_dict(section_notes.get("experience", {}), "section_notes.experience"),
                    "section_notes.experience",
                ),
                education=_build_section_decision_notes(
                    _require_dict(section_notes.get("education", {}), "section_notes.education"),
                    "section_notes.education",
                ),
                general_structure=_build_section_decision_notes(
                    _require_dict(section_notes.get("general_structure", {}), "section_notes.general_structure"),
                    "section_notes.general_structure",
                ),
            ),
            final_one_page_cv_draft=FinalOnePageCVDraft(
                title=str(final_cv_draft.get("title", "")).strip(),
                profile_summary=str(final_cv_draft.get("profile_summary", "")).strip(),
                skills=_require_list(final_cv_draft.get("skills", []), "final_one_page_cv_draft.skills"),
                experience=_require_list(final_cv_draft.get("experience", []), "final_one_page_cv_draft.experience"),
                projects=_require_list(final_cv_draft.get("projects", []), "final_one_page_cv_draft.projects"),
                education=_require_list(final_cv_draft.get("education", []), "final_one_page_cv_draft.education"),
                additional_sections=_require_list(
                    final_cv_draft.get("additional_sections", []),
                    "final_one_page_cv_draft.additional_sections",
                ),
            ),
            optional_extra_details=_require_list(result.get("optional_extra_details", []), "optional_extra_details"),
            what_not_to_claim=_require_list(result.get("what_not_to_claim", []), "what_not_to_claim"),
            cover_letter=str(result["cover_letter"]).strip(),
            key_points_to_highlight=_require_list(
                result.get("key_points_to_highlight", []),
                "key_points_to_highlight",
            ),
            raw_response=result.get("_raw_response"),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(status_code=502, detail="Claude returned an unexpected tailoring format.") from exc

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
