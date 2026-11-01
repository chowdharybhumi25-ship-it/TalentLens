# TalentLens – AI-Powered Smart Recruitment and Candidate Recommendation System

> **Recruiter-First Intelligent Recruitment Assistant with Transparent, Multi-Factor Candidate Scoring & Evaluation**

---

## 1. Project Introduction

**TalentLens** is a presentation-ready recruitment analytics and candidate recommendation platform engineered to streamline the end-to-end talent acquisition workflow. Designed with a clean SaaS aesthetic, TalentLens bridges the gap between unstructured resume PDFs and structured hiring decision-making. 

The system acts as an **assistive recommendation copilot** for human recruiters—never making autonomous black-box decisions, but instead illuminating candidate qualifications, skill alignments, experience thresholds, and contextual relevance.

---

## 2. Problem Statement

Modern recruitment pipelines suffer from significant friction:
- **High Resume Volume:** Recruiters receive hundreds of resumes for single requisitions, leading to cognitive fatigue and oversight.
- **Unstructured Information:** PDFs lack standardized formatting, making manual cross-referencing of technical skills and certifications labor-intensive.
- **Black-Box AI Skepticism:** Generic generative AI matchers often produce unpredictable, hallucinated scores without explaining *why* a candidate was recommended.
- **Compliance & Explainability:** Hiring workflows require transparent, audit-ready criteria showing exact breakdowns for required skills, domain experience, and role similarity.

TalentLens addresses these challenges by implementing an **explainable, deterministic multi-factor recommendation engine** combined with real-time PDF extraction and an interactive recruiter dashboard.

---

## 3. Project Objectives

1. **Job Requisition Benchmarking:** Enable recruiters to define job roles with department context, mandatory skills, preferred bonus skills, and minimum experience thresholds.
2. **Automated Resume Parsing:** Ingest multiple candidate PDF resumes simultaneously, extracting contact details, technical skills, years of experience, education, projects, and certifications using PyMuPDF.
3. **Explainable AI Matching:** Calculate a transparent, normalized compatibility score (0–100%) broken down into 4 clear pillars:
   - **Required Skills Match:** 40%
   - **Job Description & Resume Semantic Similarity (TF-IDF + Cosine):** 25%
   - **Preferred Skills Match:** 15%
   - **Experience Fit:** 20%
4. **Candidate Ranking & Filtering:** Sort candidates by suitability category (**Strong**, **Moderate**, **Low**) with granular experience, status, and skill filters.
5. **Head-to-Head Comparison:** Offer side-by-side candidate comparison with an interactive Plotly radar chart.
6. **Recruitment Pipeline Management:** Move candidates through structured stages (*New*, *Shortlisted*, *Interview*, *Offer*, *Rejected*) and export comprehensive CSV hiring reports.

---

## 4. Key Features

- **Recruiter Dashboard:** Real-time KPI metric cards (Total Candidates, Active Jobs, Shortlisted, Awaiting Evaluation), recommendation distribution donut chart, pipeline stage funnel, and audit trail of recent activities.
- **Active Job Benchmarking:** Switch between multiple job requisitions seamlessly; all scoring, ranking, and comparisons automatically recalibrate against the selected role.
- **Batch PDF Resume Ingestion:** Upload multiple PDFs at once with progress tracking and fail-safe handling of unreadable or corrupt documents.
- **Transparent Multi-Factor Scoring:** Pure mathematical and classical NLP formulation (TF-IDF vector space model) with zero random numbers or paid API dependencies.
- **Candidate Dossier Profile:** In-depth view displaying extracted credentials, matched vs. missing skills, candidate strengths, and areas requiring recruiter validation.
- **Plotly Competency Radar:** Interactive visual polygon comparing up to 3 candidates simultaneously across 5 dimensions.
- **Recruitment Kanban Pipeline:** Visual stage tracking with single-click candidate status updates.
- **CSV Report Export:** Downloadable spreadsheet of all applicant metrics, scores, categories, and contact info.
- **One-Click Demo Reset:** Preloaded demo dataset featuring 1 active Python Developer requisition, 6 realistic synthetic PDF resumes, and populated pipeline distributions.

---

## 5. Technology Stack

- **Frontend Interface:** [Streamlit](https://streamlit.io/) (Enhanced with custom dark navy/blue SaaS styling)
- **Backend & Logic:** Python 3.10+
- **Database:** SQLite3 (Embedded, persistent relational schema with `ROW` factory)
- **Document Text Extraction:** [PyMuPDF](https://pymupdf.readthedocs.io/) (`pymupdf`)
- **Natural Language Processing:** [Scikit-Learn](https://scikit-learn.org/) (`TfidfVectorizer`, `cosine_similarity`)
- **Data Manipulation:** [Pandas](https://pandas.pydata.org/) & [NumPy](https://numpy.org/)
- **Data Visualization:** [Plotly Express & Graph Objects](https://plotly.com/python/)

> **Zero External Costs:** Operates 100% locally on Windows, macOS, or Linux without requiring OpenAI keys, HuggingFace tokens, Docker, or external network access.

---

## 6. Architecture Overview

```
+-------------------------------------------------------------------------------+
|                             Streamlit UI Layer                                |
|  (Dashboard | Job Mgmt | Resume Upload | Ranking | Profile | Radar | Pipeline)|
+-------------------------------------------------------------------------------+
                                      |
                                      v
+-------------------------------------------------------------------------------+
|                       TalentLens Engine (engine.py)                           |
|  +---------------------------+       +-------------------------------------+  |
|  |     PyMuPDF Extraction    |       |      Explainable Matching Engine    |  |
|  |  - Text Extraction        |       |  - Required Skills Match (40%)      |  |
|  |  - Regex Contact Parser   |  ==>  |  - TF-IDF Cosine Similarity (25%)   |  |
|  |  - Skills Taxonomy Match  |       |  - Preferred Skills Match (15%)     |  |
|  |  - Experience Normalizer  |       |  - Experience Fit Normalizer (20%)  |  |
|  +---------------------------+       +-------------------------------------+  |
+-------------------------------------------------------------------------------+
                                      |
                                      v
+-------------------------------------------------------------------------------+
|                       SQLite Persistence (database.py)                        |
|  Tables: jobs | candidates | matches | activity_log                           |
+-------------------------------------------------------------------------------+
```

---

## 7. Mathematical Matching Algorithm

The compatibility score ($S_{\text{total}} \in [0, 100]$) is computed through four transparent components:

$$S_{\text{total}} = S_{\text{req}} + S_{\text{tfidf}} + S_{\text{pref}} + S_{\text{exp}}$$

### 1. Required Skills Score ($S_{\text{req}}$) — 40% Weight
$$S_{\text{req}} = \left( \frac{|\text{Matched Required Skills}|}{|\text{Total Required Skills}|} \right) \times 40$$

### 2. Resume & Job TF-IDF Semantic Similarity ($S_{\text{tfidf}}$) — 25% Weight
Documents are vectorized using unigram/bigram TF-IDF with English stop words:
$$\mathbf{v}_{\text{job}} = \text{TF-IDF}(\text{Title} + \text{Description} + \text{Skills})$$
$$\mathbf{v}_{\text{cand}} = \text{TF-IDF}(\text{Resume Text} + \text{Skills} + \text{Projects})$$
$$\text{CosineSim} = \frac{\mathbf{v}_{\text{job}} \cdot \mathbf{v}_{\text{cand}}}{\|\mathbf{v}_{\text{job}}\| \|\mathbf{v}_{\text{cand}}\|}$$
$$S_{\text{tfidf}} = \text{CosineSim} \times 25$$

### 3. Preferred Skills Score ($S_{\text{pref}}$) — 15% Weight
$$S_{\text{pref}} = \left( \frac{|\text{Matched Preferred Skills}|}{|\text{Total Preferred Skills}|} \right) \times 15$$
*(If a job defines no preferred skills, candidate receives full 15 points).*

### 4. Experience Fit Score ($S_{\text{exp}}$) — 20% Weight
Let $E_{\text{cand}}$ be candidate experience and $E_{\text{req}}$ be job requirement:
$$S_{\text{exp}} = \begin{cases} 20, & \text{if } E_{\text{cand}} \ge E_{\text{req}} \\ \left(\frac{E_{\text{cand}}}{E_{\text{req}}}\right) \times 20, & \text{if } E_{\text{cand}} < E_{\text{req}} \end{cases}$$

### Recommendation Categories:
- **Strong Match:** $S_{\text{total}} \ge 70\%$
- **Moderate Match:** $45\% \le S_{\text{total}} < 70\%$
- **Low Match:** $S_{\text{total}} < 45\%$

---

## 8. Installation & Execution Guide

### Step 1: Clone or Open the Workspace
```bash
cd Smart_Recruitment_Recommendation_System
```

### Step 2: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 3: Generate Presentation Samples & Initialize Database
```bash
python generate_samples.py
```
*(This generates 6 realistic PDF resumes in `sample_resumes/` and preloads the benchmark dataset).*

### Step 4: Launch the Streamlit Application
```bash
streamlit run app.py
```
Open your browser at `http://localhost:8501`.

---

## 9. Live College Demonstration Script

Follow this step-by-step walkthrough to showcase the project to your instructor:

1. **Dashboard Overview (`📊 Dashboard`):**
   - Point out the active preloaded job: **Python Developer** (Engineering).
   - Review the KPI metrics (6 Candidates, 1 Active Job, Shortlisted, In Review).
   - Highlight the interactive Plotly Donut Chart (Score Distribution) and Recruitment Funnel.
   - Show the Recent Activity Audit Log.

2. **Job Management (`💼 Job Management`):**
   - Display the preloaded job requirements (Python, Flask, SQL required; AWS, Docker, Kubernetes, FastAPI preferred; 3.0 yrs min exp).
   - Demonstrate creating a second job (e.g., *Data Scientist* or *Frontend Engineer*).
   - Show how changing the active benchmark job automatically recalculates candidate fit.

3. **Resume Parser & Upload (`📄 Resume Parser & Upload`):**
   - Expand the **Pre-Generated Demo PDF Resumes** section and download sample PDFs to show real documents.
   - Drag and drop any of the sample PDFs into the uploader.
   - Click **Start Intelligent Ingestion & Parsing** to show the live progress bar and PyMuPDF text extraction.

4. **Candidate Ranking (`🏆 Candidate Ranking`):**
   - Demonstrate the ranked applicant list sorted by overall compatibility:
     - **Sophia Chen** (~77%, Strong Match)
     - **Aarav Sharma** (~77%, Strong Match)
     - **Marcus Miller** (~54%, Moderate Match - Junior exp)
     - **Priya Patel** (~48%, Moderate Match - Data focus, missing Flask)
     - **David Kim** (~21%, Low Match - Frontend React, no Python)
     - **Elena Rostova** (~17%, Low Match - Java Junior)
   - Filter by Category (*Strong*, *Moderate*, *Low*) or minimum experience slider.

5. **Detailed Candidate Profile (`👤 Candidate Profile`):**
   - Select **Aarav Sharma** or **Marcus Miller**.
   - Show the transparent 4-pillar breakdown scores out of 40, 25, 15, and 20.
   - Review candidate **Strengths** and **Areas Requiring Recruiter Validation**.
   - Demonstrate changing the candidate's stage (e.g. click **⭐ Shortlist Candidate**).

6. **Candidate Comparison (`⚖️ Candidate Comparison`):**
   - Select 2 or 3 candidates (e.g. Aarav Sharma, Marcus Miller, and Priya Patel).
   - Showcase the **Plotly Competency Radar Chart** comparing them across all 5 skill dimensions.
   - Walk through the side-by-side attribute comparison matrix.

7. **Pipeline & CSV Export (`📋 Recruitment Pipeline`):**
   - Show the 5-column recruitment board (*New*, *Shortlisted*, *Interview*, *Offer*, *Rejected*).
   - Click **📥 Export Candidate Report (CSV)** and show the downloaded CSV containing full applicant scoring data.

8. **Reset Demo Data (`⚙️ Reset & Demo Data`):**
   - Explain how any evaluator can wipe and instantly restore the pristine demonstration environment with one click.

---

## 10. Verification & Test Suite

An automated test suite is provided to verify system integrity:
```bash
python test_talentlens.py
```
**Test Coverage:**
- SQLite database schema initialization and persistence.
- PyMuPDF text extraction and entity parsing.
- TF-IDF Cosine Similarity calculation.
- Mathematical multi-factor weighting formula.
- Candidate ranking ordering and category thresholds.
- Pipeline stage transitions and CSV export integrity.

---

## 11. Limitations & Future Scope

### Current Limitations:
- **Rule-based Entity Extraction:** Relies on standardized headings and regex matching rather than a custom-trained NER model.
- **Language Scope:** Optimized for English-language resumes.
- **Document Format:** PDF format is natively supported; docx files currently require conversion to PDF.

### Future Scope:
- Integration of local open-source transformer models (e.g., SpaCy or HuggingFace Sentence Transformers) for deeper semantic understanding.
- Automated interview question generation based on detected missing skills.
- Direct email notification integration with applicant tracking systems (ATS).
