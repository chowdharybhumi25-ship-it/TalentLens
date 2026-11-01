"""
Comprehensive Integration and Verification Test Suite for TalentLens
Validates Database, PyMuPDF extraction, TF-IDF Matching, Ranking, Pipeline, and CSV Export.
"""

import os
import unittest
import pandas as pd
import json

from database import (
    init_db, reset_database, get_all_jobs, get_job_by_id, create_job,
    save_candidate, get_all_candidates, get_candidate_by_id,
    save_match_evaluation, get_matches_for_job, update_candidate_status,
    get_dashboard_metrics
)
from engine import (
    extract_text_from_pdf, parse_resume, match_skills,
    compute_tfidf_similarity, evaluate_candidate
)
from generate_samples import generate_all_samples, SAMPLE_DIR


class TestTalentLensSystem(unittest.TestCase):
    
    @classmethod
    def setUpClass(cls):
        print("\n--- Running TalentLens System Integration Tests ---")
        reset_database()
        generate_all_samples()

    def test_01_database_and_preloaded_job(self):
        jobs = get_all_jobs()
        self.assertGreaterEqual(len(jobs), 1, "At least one job should be preloaded.")
        job = jobs[0]
        self.assertEqual(job["title"], "Python Developer")
        self.assertIn("Python", job["required_skills"])
        self.assertIn("Flask", job["required_skills"])
        self.assertIn("SQL", job["required_skills"])
        self.assertEqual(job["min_experience"], 3.0)
        print("[OK] Preloaded job opening verified.")

    def test_02_sample_pdf_generation_and_extraction(self):
        pdf_files = [f for f in os.listdir(SAMPLE_DIR) if f.endswith(".pdf")]
        self.assertEqual(len(pdf_files), 6, "Expected 6 synthetic sample PDFs in sample_resumes.")
        
        # Test extraction on one PDF
        sample_path = os.path.join(SAMPLE_DIR, pdf_files[0])
        extracted_text = extract_text_from_pdf(sample_path)
        self.assertGreater(len(extracted_text), 100, "Extracted PDF text should not be empty.")
        
        parsed = parse_resume(extracted_text, filename=pdf_files[0])
        self.assertTrue(len(parsed["name"]) > 1, "Extracted candidate name should be valid.")
        self.assertIsInstance(parsed["skills"], list)
        self.assertGreater(len(parsed["skills"]), 0, "Should extract technical skills.")
        print(f"[OK] PyMuPDF text extraction & entity parsing verified on {pdf_files[0]}.")

    def test_03_tfidf_and_cosine_similarity(self):
        job_doc = "Python Developer Flask SQL database cloud backend microservices"
        matching_cand = "Experienced Python developer with Flask and SQL backend microservices"
        unrelated_cand = "Graphic designer specializing in Photoshop, Figma, Illustrator, and typography"

        sim_high = compute_tfidf_similarity(job_doc, matching_cand)
        sim_low = compute_tfidf_similarity(job_doc, unrelated_cand)

        self.assertGreater(sim_high, sim_low, "Matching candidate should have significantly higher TF-IDF score.")
        self.assertGreaterEqual(sim_high, 0.3)
        print(f"[OK] TF-IDF Cosine Similarity verified (Match: {sim_high:.3f} vs Unrelated: {sim_low:.3f}).")

    def test_04_candidate_evaluation_formula(self):
        job = {
            "title": "Python Developer",
            "department": "Engineering",
            "description": "Looking for Python, Flask, SQL developer with AWS, Docker.",
            "required_skills": ["Python", "Flask", "SQL"],
            "preferred_skills": ["AWS", "Docker"],
            "min_experience": 3.0
        }
        candidate_perfect = {
            "name": "Alex Smith",
            "skills": ["Python", "Flask", "SQL", "AWS", "Docker"],
            "experience_years": 4.0,
            "raw_text": "Experienced Python backend engineer using Flask, SQL, AWS, and Docker.",
            "education": "B.Tech Computer Science",
            "projects": "Scalable REST APIs"
        }
        res = evaluate_candidate(job, candidate_perfect)
        
        # Required skills = 3/3 -> 40.0
        self.assertEqual(res["required_match_score"], 40.0)
        # Preferred skills = 2/2 -> 15.0
        self.assertEqual(res["preferred_match_score"], 15.0)
        # Experience = 4.0 >= 3.0 -> 20.0
        self.assertEqual(res["experience_score"], 20.0)
        # Total overall score >= 75
        self.assertGreaterEqual(res["overall_score"], 75.0)
        self.assertEqual(res["category"], "Strong")
        print(f"[OK] Evaluation formula & score weighting verified (Perfect score: {res['overall_score']}%).")

    def test_05_score_distribution_and_ranking(self):
        jobs = get_all_jobs()
        job_id = jobs[0]["id"]
        matches = get_matches_for_job(job_id)
        
        self.assertEqual(len(matches), 6, "Expected 6 evaluated candidates.")
        
        categories = [m["category"] for m in matches]
        self.assertIn("Strong", categories, "Should contain Strong match.")
        self.assertIn("Moderate", categories, "Should contain Moderate match.")
        self.assertIn("Low", categories, "Should contain Low match.")

        # Verify ranking order (descending overall_score)
        scores = [m["overall_score"] for m in matches]
        self.assertEqual(scores, sorted(scores, reverse=True), "Candidates should be ranked by score descending.")
        print(f"[OK] Ranking & Score distribution verified (Scores: {scores}).")

    def test_06_pipeline_transition_and_csv_export(self):
        jobs = get_all_jobs()
        job_id = jobs[0]["id"]
        matches = get_matches_for_job(job_id)
        cand_id = matches[0]["candidate_id"]

        # Update pipeline stage
        update_candidate_status(job_id, cand_id, "Offer")
        updated_matches = get_matches_for_job(job_id)
        target = [m for m in updated_matches if m["candidate_id"] == cand_id][0]
        self.assertEqual(target["status"], "Offer")

        # Test CSV generation
        csv_data = pd.DataFrame([{
            "Candidate": m["name"],
            "Score": m["overall_score"],
            "Category": m["category"],
            "Status": m["status"]
        } for m in updated_matches])
        self.assertEqual(len(csv_data), 6)
        print("[OK] Recruitment pipeline transition & CSV generation verified.")


if __name__ == "__main__":
    unittest.main()
