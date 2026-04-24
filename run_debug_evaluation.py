#!/usr/bin/env python3
"""
Debug evaluation script for Resume Ranker.
Runs the full pipeline on 3 real resumes with a realistic Junior Developer JD.
Prints corrected rankings and scores.
"""
import sys
import os

# Ensure backend is importable
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backend.workflows.pipeline import run_pipeline
from backend.tools.exporter import export_to_json, export_shortlist_report

# Realistic Junior Software Developer JD
JUNIOR_DEV_JD = """
Junior Software Developer

We are looking for a Junior Software Developer to join our engineering team.
This is an entry-level role. Freshers can apply.

Required Skills:
- Python
- SQL
- HTML/CSS
- JavaScript

Preferred Skills:
- React or any frontend framework
- Flask or FastAPI or Django
- Git
- REST API development

Experience:
- 0 to 2 years of software development experience

Education:
- BCA / BSc CS / BTech / Related Degree

Soft Skills:
- Communication
- Teamwork
- Problem solving

Location: Mumbai / Pune / Bengaluru / Remote India

Role Summary:
This role is ideal for candidates with academic projects, internship simulations,
strong coding interest, and willingness to learn.
"""

# Resume paths from existing uploads
RESUME_PATHS = [
    "uploads/5238f7ed-251f-40e6-9651-2556ffbd75cc/Nandita Resume.pdf.pdf",
    "uploads/5238f7ed-251f-40e6-9651-2556ffbd75cc/Niranjan patil resume new.pdf",
    "uploads/5238f7ed-251f-40e6-9651-2556ffbd75cc/Omkar_final CV.pdf",
]


def main():
    print("=" * 70)
    print("RESUME RANKER — DEBUG EVALUATION")
    print("=" * 70)
    print(f"\nJob Description: Junior Software Developer (Entry-Level)")
    print(f"Resumes to evaluate: {len(RESUME_PATHS)}")
    print("-" * 70)

    # Verify files exist
    for p in RESUME_PATHS:
        abs_p = os.path.join(os.path.dirname(__file__), p)
        if not os.path.exists(abs_p):
            print(f"WARNING: File not found: {abs_p}")
        else:
            print(f"OK: {p}")

    print("-" * 70)
    print("\nRunning pipeline...\n")

    final_state = run_pipeline(
        jd_text=JUNIOR_DEV_JD,
        resume_paths=RESUME_PATHS,
        run_id="debug-eval-001",
    )

    ranked = final_state.get("ranked_candidates", [])
    job = final_state.get("job_profile")

    print("=" * 70)
    print("RESULTS")
    print("=" * 70)

    if not ranked:
        print("ERROR: No candidates were ranked.")
        return

    print(f"\nJob Title: {job.role_title if job else 'Unknown'}")
    print(f"Role Type: {job.role_type if job else 'Unknown'}")
    print(f"Must-Have Skills ({len(job.must_have_skills) if job else 0}): {', '.join(job.must_have_skills[:10]) if job else 'N/A'}")
    print(f"Preferred Skills ({len(job.preferred_skills) if job else 0}): {', '.join(job.preferred_skills[:10]) if job else 'N/A'}")
    print(f"Min Experience: {job.min_experience_years if job else 'N/A'} years")
    print()

    shortlist_count = 0
    hold_count = 0
    reject_count = 0

    for sc in ranked:
        c = sc.candidate
        sb = sc.score_breakdown
        r = sc.reasoning

        rec = r.recommendation.value if r else "unknown"
        if rec == "shortlist":
            shortlist_count += 1
        elif rec == "hold":
            hold_count += 1
        else:
            reject_count += 1

        print(f"Rank #{sc.rank} — {c.name or 'Unknown'} ({c.file_name})")
        print(f"  Total Score: {sb.total_score:.1f}/100")
        print(f"  Recommendation: {rec.upper()}")
        print(f"  Confidence: {r.confidence_level:.0%}" if r else "  Confidence: N/A")
        print(f"  Experience: {c.total_experience_years} years")
        print(f"  Skills ({len(c.skills)}): {', '.join(c.skills[:8])}{'...' if len(c.skills) > 8 else ''}")
        print(f"  Projects: {len(c.projects)}")
        print(f"  Education: {len(c.education)}")
        print(f"  Certifications: {len(c.certifications)}")
        print(f"  Score Breakdown:")
        print(f"    - Role Experience:  {sb.role_experience.raw_score:.1f} (weight {sb.role_experience.weight}%)")
        print(f"    - Projects:         {sb.relevant_projects.raw_score:.1f} (weight {sb.relevant_projects.weight}%)")
        print(f"    - Certifications:   {sb.certifications.raw_score:.1f} (weight {sb.certifications.weight}%)")
        print(f"    - Education:        {sb.education.raw_score:.1f} (weight {sb.education.weight}%)")
        print(f"    - Soft Signals:     {sb.soft_signals.raw_score:.1f} (weight {sb.soft_signals.weight}%)")
        print(f"    - Semantic Bonus:   +{sb.semantic_similarity * 5:.1f}")
        print(f"    - Penalties:        -{sb.penalty_deductions:.1f}")
        if r:
            print(f"  Summary: {r.summary}")
            if r.strengths:
                print(f"  Strengths: {', '.join(r.strengths[:3])}")
            if r.gaps:
                print(f"  Gaps: {', '.join(r.gaps[:3])}")
        print("-" * 70)

    print(f"\nSUMMARY: Shortlisted={shortlist_count}  Hold={hold_count}  Rejected={reject_count}")
    print("=" * 70)

    # Export results
    export_to_json("debug-eval-001", ranked, job)
    export_shortlist_report("debug-eval-001", ranked, job)
    print("\nExports saved to exports/debug-eval-001_results.json")
    print("               exports/debug-eval-001_shortlist_report.txt")


if __name__ == "__main__":
    main()
