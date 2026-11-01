"""
TalentLens – AI-Powered Smart Recruitment and Candidate Recommendation System
Enterprise SaaS Redesign
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import json
import os
import io
from datetime import datetime

from database import (
    init_db, get_all_jobs, get_job_by_id, create_job,
    save_candidate, get_all_candidates, get_candidate_by_id,
    save_match_evaluation, get_matches_for_job, get_match_by_candidate_and_job,
    update_candidate_status, get_dashboard_metrics, get_recent_activity,
    reset_database, log_activity
)
from engine import (
    extract_text_from_pdf, parse_resume, evaluate_candidate
)
from generate_samples import generate_all_samples, SAMPLE_DIR

# --- STREAMLIT PAGE CONFIG ---
st.set_page_config(
    page_title="TalentLens | Enterprise Recruitment AI",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- ENSURE INITIALIZED DATABASE ---
init_db()
existing_jobs = get_all_jobs()
if not existing_jobs:
    generate_all_samples()
    existing_jobs = get_all_jobs()

# --- BULLETPROOF ENTERPRISE SAAS CUSTOM CSS ---
ENTERPRISE_CSS = """
<style>
    /* Global Typography */
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=Inter:wght@400;500;600;700&display=swap');

    html, body, [class*="css"], .stMarkdown, .stText {
        font-family: 'Plus Jakarta Sans', 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
    }

    /* 1. Bulletproof Main Canvas Background */
    [data-testid="stAppViewContainer"],
    [data-testid="stAppViewContainer"] > .main,
    [data-testid="stApp"],
    .stApp {
        background-color: #f8fafc !important;
        background: #f8fafc !important;
        color: #0f172a !important;
    }

    /* Top Streamlit Header Bar */
    [data-testid="stHeader"] {
        background-color: rgba(248, 250, 252, 0.9) !important;
        backdrop-filter: blur(8px) !important;
    }

    /* Main Container Padding */
    .main .block-container {
        padding-top: 1.5rem !important;
        padding-bottom: 3rem !important;
        max-width: 1400px;
    }

    /* 2. Bulletproof Sidebar Styling (Deep Navy) */
    [data-testid="stSidebar"],
    [data-testid="stSidebarContent"],
    [data-testid="stSidebarUserContent"],
    section[data-testid="stSidebar"],
    section[data-testid="stSidebar"] > div {
        background: #090e1a !important;
        background-color: #090e1a !important;
        background-image: linear-gradient(180deg, #090e1a 0%, #0f172a 100%) !important;
        color: #f8fafc !important;
        border-right: 1px solid #1e293b !important;
    }

    [data-testid="stSidebarContent"] p,
    [data-testid="stSidebarContent"] span,
    [data-testid="stSidebarContent"] label,
    [data-testid="stSidebarContent"] div {
        color: #e2e8f0 !important;
    }

    /* Sidebar Selectbox */
    [data-testid="stSidebarContent"] div[data-baseweb="select"] > div {
        background-color: #1e293b !important;
        border: 1px solid #334155 !important;
        color: #ffffff !important;
        border-radius: 8px !important;
    }
    [data-testid="stSidebarContent"] div[data-baseweb="select"] span {
        color: #ffffff !important;
    }

    /* Sidebar Radio Buttons */
    [data-testid="stSidebarContent"] .stRadio label {
        padding: 6px 12px !important;
        border-radius: 8px !important;
        cursor: pointer !important;
        transition: all 0.2s ease !important;
    }
    [data-testid="stSidebarContent"] .stRadio label:hover {
        background-color: rgba(255, 255, 255, 0.08) !important;
    }
    [data-testid="stSidebarContent"] .stRadio div[aria-checked="true"] {
        background-color: #4f46e5 !important;
        border-color: #4f46e5 !important;
    }

    /* Sidebar Brand Card */
    .saas-brand-card {
        padding: 16px 14px !important;
        background: rgba(30, 41, 59, 0.7) !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        border-radius: 14px !important;
        margin-bottom: 20px !important;
        display: flex !important;
        align-items: center !important;
        gap: 12px !important;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2) !important;
    }
    .saas-logo-icon {
        width: 42px !important;
        height: 42px !important;
        border-radius: 10px !important;
        background: linear-gradient(135deg, #4f46e5 0%, #3b82f6 100%) !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        font-size: 22px !important;
        color: #ffffff !important;
        box-shadow: 0 2px 8px rgba(79, 70, 229, 0.4) !important;
    }
    .saas-brand-title {
        font-size: 20px !important;
        font-weight: 800 !important;
        letter-spacing: -0.4px !important;
        color: #ffffff !important;
        margin: 0 !important;
        line-height: 1.1 !important;
    }
    .saas-brand-sub {
        font-size: 11px !important;
        font-weight: 700 !important;
        text-transform: uppercase !important;
        letter-spacing: 0.8px !important;
        color: #818cf8 !important;
        margin-top: 2px !important;
    }

    /* Active Job Card in Sidebar */
    .sidebar-job-card {
        background: rgba(15, 23, 42, 0.85) !important;
        border: 1px solid #334155 !important;
        border-radius: 12px !important;
        padding: 14px !important;
        margin-bottom: 18px !important;
    }

    /* 3. Top Greeting Banner */
    .greeting-banner {
        background-color: #ffffff !important;
        background: #ffffff !important;
        border: 1px solid #e2e8f0 !important;
        border-left: 5px solid #4f46e5 !important;
        border-radius: 16px !important;
        padding: 24px 28px !important;
        margin-bottom: 24px !important;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05), 0 1px 2px rgba(0, 0, 0, 0.03) !important;
        display: flex !important;
        justify-content: space-between !important;
        align-items: center !important;
    }
    .greeting-tag {
        display: inline-block !important;
        font-size: 11px !important;
        font-weight: 700 !important;
        text-transform: uppercase !important;
        letter-spacing: 1px !important;
        color: #4f46e5 !important;
        background: #eef2ff !important;
        padding: 3px 10px !important;
        border-radius: 20px !important;
        margin-bottom: 6px !important;
    }
    .greeting-title {
        font-size: 26px !important;
        font-weight: 800 !important;
        color: #0f172a !important;
        margin: 0 !important;
        letter-spacing: -0.5px !important;
    }
    .greeting-subtitle {
        font-size: 14px !important;
        color: #64748b !important;
        margin-top: 4px !important;
        font-weight: 500 !important;
    }

    /* 4. Premium KPI Metric Cards */
    .kpi-card {
        background-color: #ffffff !important;
        background: #ffffff !important;
        border: 1px solid #e2e8f0 !important;
        border-radius: 14px !important;
        padding: 20px 22px !important;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04) !important;
        transition: transform 0.2s ease, box-shadow 0.2s ease !important;
    }
    .kpi-card:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 8px 18px rgba(0, 0, 0, 0.06) !important;
    }
    .kpi-header {
        display: flex !important;
        justify-content: space-between !important;
        align-items: center !important;
        margin-bottom: 8px !important;
    }
    .kpi-title {
        font-size: 13px !important;
        font-weight: 700 !important;
        color: #64748b !important;
        text-transform: uppercase !important;
        letter-spacing: 0.5px !important;
    }
    .kpi-icon-pill {
        width: 32px !important;
        height: 32px !important;
        border-radius: 8px !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        font-size: 15px !important;
    }
    .kpi-value {
        font-size: 32px !important;
        font-weight: 800 !important;
        color: #0f172a !important;
        line-height: 1.1 !important;
        letter-spacing: -0.5px !important;
    }
    .kpi-subtext {
        font-size: 12px !important;
        color: #94a3b8 !important;
        margin-top: 6px !important;
        font-weight: 500 !important;
    }

    /* 5. Enterprise White Cards */
    .saas-card {
        background-color: #ffffff !important;
        background: #ffffff !important;
        border: 1px solid #e2e8f0 !important;
        border-radius: 14px !important;
        padding: 24px !important;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04) !important;
        margin-bottom: 22px !important;
    }
    .saas-card-title {
        font-size: 18px !important;
        font-weight: 700 !important;
        color: #0f172a !important;
        margin-bottom: 16px !important;
        display: flex !important;
        align-items: center !important;
        gap: 8px !important;
        letter-spacing: -0.3px !important;
    }

    /* 6. Match Category Badges */
    .badge-match {
        font-size: 12px !important;
        font-weight: 700 !important;
        padding: 4px 12px !important;
        border-radius: 24px !important;
        display: inline-flex !important;
        align-items: center !important;
        gap: 5px !important;
    }
    .badge-strong {
        background-color: #ecfdf5 !important;
        color: #065f46 !important;
        border: 1px solid #a7f3d0 !important;
    }
    .badge-moderate {
        background-color: #fffbeb !important;
        color: #92400e !important;
        border: 1px solid #fde68a !important;
    }
    .badge-low {
        background-color: #fef2f2 !important;
        color: #991b1b !important;
        border: 1px solid #fecaca !important;
    }

    /* 7. Pipeline Stage Pills */
    .stage-pill {
        font-size: 11px !important;
        font-weight: 700 !important;
        text-transform: uppercase !important;
        letter-spacing: 0.5px !important;
        padding: 4px 10px !important;
        border-radius: 20px !important;
        display: inline-block !important;
    }
    .stage-new { background: #e0f2fe !important; color: #0369a1 !important; border: 1px solid #bae6fd !important; }
    .stage-shortlisted { background: #fef9c3 !important; color: #854d0e !important; border: 1px solid #fde047 !important; }
    .stage-interview { background: #ede9fe !important; color: #5b21b6 !important; border: 1px solid #ddd6fe !important; }
    .stage-offer { background: #dcfce7 !important; color: #15803d !important; border: 1px solid #bbf7d0 !important; }
    .stage-rejected { background: #f1f5f9 !important; color: #64748b !important; border: 1px solid #e2e8f0 !important; }

    /* 8. Skill Tags */
    .skill-chip {
        display: inline-block !important;
        font-size: 12px !important;
        font-weight: 600 !important;
        padding: 4px 10px !important;
        border-radius: 6px !important;
        margin: 2px 3px !important;
    }
    .skill-chip-default {
        background-color: #f1f5f9 !important;
        color: #334155 !important;
        border: 1px solid #e2e8f0 !important;
    }
    .skill-chip-matched {
        background-color: #eff6ff !important;
        color: #1d4ed8 !important;
        border: 1px solid #bfdbfe !important;
    }
    .skill-chip-missing {
        background-color: #fef2f2 !important;
        color: #b91c1c !important;
        border: 1px solid #fecaca !important;
    }

    /* 9. Candidate Item Card */
    .applicant-item {
        background-color: #ffffff !important;
        background: #ffffff !important;
        border: 1px solid #e2e8f0 !important;
        border-radius: 12px !important;
        padding: 20px 22px !important;
        margin-bottom: 14px !important;
        box-shadow: 0 1px 2px rgba(0, 0, 0, 0.03) !important;
        transition: border-color 0.15s ease, box-shadow 0.15s ease !important;
    }
    .applicant-item:hover {
        border-color: #cbd5e1 !important;
        box-shadow: 0 6px 14px rgba(0, 0, 0, 0.05) !important;
    }

    /* Score Progress Bar */
    .score-bar-bg {
        width: 100% !important;
        height: 8px !important;
        background-color: #f1f5f9 !important;
        border-radius: 4px !important;
        overflow: hidden !important;
        margin-top: 6px !important;
    }
    .score-bar-fill-strong { height: 100% !important; background: linear-gradient(90deg, #10b981, #059669) !important; }
    .score-bar-fill-moderate { height: 100% !important; background: linear-gradient(90deg, #f59e0b, #d97706) !important; }
    .score-bar-fill-low { height: 100% !important; background: linear-gradient(90deg, #ef4444, #dc2626) !important; }

    /* Streamlit High Contrast Inputs */
    .stTextInput input, .stTextArea textarea, .stNumberInput input {
        border-radius: 8px !important;
        border: 1.5px solid #cbd5e1 !important;
        color: #0f172a !important;
        font-weight: 500 !important;
        background-color: #ffffff !important;
    }

    /* Buttons */
    .stButton button {
        border-radius: 8px !important;
        font-weight: 600 !important;
        padding: 8px 16px !important;
        letter-spacing: -0.2px !important;
    }
</style>
"""
st.markdown(ENTERPRISE_CSS, unsafe_allow_html=True)


# --- SESSION STATE MANAGEMENT ---
if "active_job_id" not in st.session_state:
    st.session_state.active_job_id = existing_jobs[0]["id"] if existing_jobs else None

if "selected_candidate_id" not in st.session_state:
    st.session_state.selected_candidate_id = None


# --- SIDEBAR: BRANDING & NAVIGATION ---
with st.sidebar:
    # 1. TalentLens Brand Header
    st.markdown("""
    <div class="saas-brand-card">
        <div class="saas-logo-icon">🎯</div>
        <div>
            <div class="saas-brand-title">TalentLens</div>
            <div class="saas-brand-sub">Enterprise Suite</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # 2. Active Benchmark Job Selector
    all_jobs = get_all_jobs()
    if all_jobs:
        job_options = {j["id"]: f"{j['title']} ({j['department']})" for j in all_jobs}
        job_ids = list(job_options.keys())

        current_idx = 0
        if st.session_state.active_job_id in job_ids:
            current_idx = job_ids.index(st.session_state.active_job_id)

        selected_id = st.selectbox(
            "💼 Active Requisition",
            options=job_ids,
            index=current_idx,
            format_func=lambda x: job_options[x],
            help="Select the benchmark job opening. All candidate scoring and analytics instantly align with this requisition."
        )
        st.session_state.active_job_id = selected_id
        active_job = get_job_by_id(selected_id)

        # Quick Active Job Spec Summary Card in Sidebar
        if active_job:
            req_pills = "".join([f"<span class='skill-chip skill-chip-matched' style='font-size:10px;padding:2px 6px;'>{s}</span>" for s in active_job['required_skills'][:3]])
            st.markdown(f"""
            <div class="sidebar-job-card">
                <div style="font-size:11px;font-weight:700;color:#94a3b8;text-transform:uppercase;margin-bottom:4px;">Benchmark Specs</div>
                <div style="font-size:13px;font-weight:700;color:#ffffff;">{active_job['title']}</div>
                <div style="font-size:11px;color:#94a3b8;margin-bottom:6px;">Min Exp: <strong style="color:#e2e8f0;">{active_job['min_experience']} yrs</strong></div>
                <div>{req_pills}</div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.warning("No jobs defined yet.")
        active_job = None

    st.markdown("<hr style='border-color:#1e293b;margin:12px 0;'>", unsafe_allow_html=True)

    # 3. Sidebar Navigation Radio
    nav_selection = st.radio(
        "Navigation",
        options=[
            "📊 Dashboard",
            "💼 Job Management",
            "📄 Resume Screening",
            "👥 Candidates",
            "⚖️ Candidate Comparison",
            "📋 Shortlist & Pipeline",
            "📈 Reports & Analytics",
            "⚙️ Settings"
        ],
        index=0
    )

    st.markdown("<hr style='border-color:#1e293b;margin:14px 0;'>", unsafe_allow_html=True)

    # Recruiter Profile Badge
    st.markdown("""
    <div style="padding:10px;background:rgba(30,41,59,0.5);border-radius:10px;display:flex;align-items:center;gap:10px;">
        <div style="width:34px;height:34px;border-radius:50%;background:#3b82f6;display:flex;align-items:center;justify-content:center;font-weight:700;font-size:13px;color:#fff;">
            HR
        </div>
        <div>
            <div style="font-size:12px;font-weight:700;color:#f8fafc;">Lead Recruiter</div>
            <div style="font-size:10px;color:#94a3b8;">Talent Intelligence Hub</div>
        </div>
    </div>
    """, unsafe_allow_html=True)


# ==============================================================================
# MODULE A: DASHBOARD
# ==============================================================================
if nav_selection == "📊 Dashboard":
    # 1. Enterprise Greeting Header
    job_label = f"{active_job['title']} ({active_job['department']})" if active_job else "All Requisitions"
    st.markdown(f"""
    <div class="greeting-banner">
        <div>
            <span class="greeting-tag">TALENT INTELLIGENCE PLATFORM</span>
            <h1 class="greeting-title">Good morning, Recruiter</h1>
            <p class="greeting-subtitle">Your intelligent recruitment command centre.</p>
        </div>
        <div style="text-align:right;">
            <div style="font-size:12px;font-weight:600;color:#64748b;text-transform:uppercase;">Active Benchmark</div>
            <div style="font-size:15px;font-weight:700;color:#1e293b;margin-top:2px;">💼 {job_label}</div>
            <span style="font-size:11px;color:#10b981;font-weight:600;">● Engine Online & Synced</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    if not active_job:
        st.info("Please create a job in Job Management to start evaluating.")
        st.stop()

    metrics = get_dashboard_metrics(active_job["id"])
    matches = get_matches_for_job(active_job["id"])

    # Calculate Average Match Score
    avg_score = round(sum(m["overall_score"] for m in matches) / len(matches), 1) if matches else 0.0

    # 2. KPI Metrics Grid (Total Candidates, Active Jobs, Shortlisted, Average Match Score)
    k1, k2, k3, k4 = st.columns(4)
    with k1:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-header">
                <span class="kpi-title">Total Candidates</span>
                <span class="kpi-icon-pill" style="background:#eff6ff;color:#3b82f6;">👥</span>
            </div>
            <div class="kpi-value">{metrics['total_candidates']}</div>
            <div class="kpi-subtext">Across talent pool</div>
        </div>
        """, unsafe_allow_html=True)

    with k2:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-header">
                <span class="kpi-title">Active Jobs</span>
                <span class="kpi-icon-pill" style="background:#f5f3ff;color:#8b5cf6;">💼</span>
            </div>
            <div class="kpi-value">{metrics['active_jobs']}</div>
            <div class="kpi-subtext">Open requisitions</div>
        </div>
        """, unsafe_allow_html=True)

    with k3:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-header">
                <span class="kpi-title">Shortlisted</span>
                <span class="kpi-icon-pill" style="background:#fefce8;color:#eab308;">⭐</span>
            </div>
            <div class="kpi-value">{metrics['shortlisted']}</div>
            <div class="kpi-subtext">Qualified for interview</div>
        </div>
        """, unsafe_allow_html=True)

    with k4:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-header">
                <span class="kpi-title">Average Match Score</span>
                <span class="kpi-icon-pill" style="background:#ecfdf5;color:#10b981;">🎯</span>
            </div>
            <div class="kpi-value">{avg_score}%</div>
            <div class="kpi-subtext">Benchmark compatibility</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # 3. Interactive Charts (Match Distribution & Recruitment Pipeline)
    col_chart_l, col_chart_r = st.columns(2)

    with col_chart_l:
        st.markdown("""
        <div class="saas-card">
            <div class="saas-card-title"><span>🥧</span> Candidate Match Distribution</div>
        """, unsafe_allow_html=True)
        cat_counts = metrics["categories"]
        if cat_counts:
            categories_order = ["Strong", "Moderate", "Low"]
            cat_data = [{"Category": cat, "Count": cat_counts.get(cat, 0)} for cat in categories_order]
            df_cat = pd.DataFrame(cat_data)

            fig_pie = px.pie(
                df_cat,
                names="Category",
                values="Count",
                color="Category",
                color_discrete_map={"Strong": "#10b981", "Moderate": "#f59e0b", "Low": "#ef4444"},
                hole=0.55
            )
            fig_pie.update_traces(
                textposition='inside',
                textinfo='percent+label',
                hovertemplate="<b>%{label} Match</b><br>Count: %{value}<br>Share: %{percent}<extra></extra>"
            )
            fig_pie.update_layout(
                margin=dict(t=10, b=10, l=10, r=10),
                height=290,
                showlegend=True,
                legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5),
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font=dict(family="Plus Jakarta Sans, sans-serif", color="#334155")
            )
            st.plotly_chart(fig_pie, use_container_width=True)
        else:
            st.info("No candidates evaluated yet for this role.")
        st.markdown("</div>", unsafe_allow_html=True)

    with col_chart_r:
        st.markdown("""
        <div class="saas-card">
            <div class="saas-card-title"><span>📊</span> Recruitment Pipeline Velocity</div>
        """, unsafe_allow_html=True)
        pipeline_counts = metrics["pipeline"]
        stages = ["New", "Shortlisted", "Interview", "Offer", "Rejected"]
        pipe_data = [{"Stage": stage, "Candidates": pipeline_counts.get(stage, 0)} for stage in stages]
        df_pipe = pd.DataFrame(pipe_data)

        fig_bar = px.bar(
            df_pipe,
            x="Stage",
            y="Candidates",
            text="Candidates",
            color="Stage",
            color_discrete_map={
                "New": "#3b82f6",
                "Shortlisted": "#f59e0b",
                "Interview": "#6366f1",
                "Offer": "#10b981",
                "Rejected": "#94a3b8"
            }
        )
        fig_bar.update_traces(
            textposition='outside',
            textfont=dict(family="Plus Jakarta Sans", weight="bold", color="#1e293b")
        )
        fig_bar.update_layout(
            margin=dict(t=20, b=10, l=10, r=10),
            height=290,
            showlegend=False,
            xaxis_title="",
            yaxis_title="Count",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(family="Plus Jakarta Sans, sans-serif", color="#334155"),
            yaxis=dict(gridcolor="#f1f5f9")
        )
        st.plotly_chart(fig_bar, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # 4. Top Recommended Candidates & Recent Activity
    row_bot1, row_bot2 = st.columns([3, 2])

    with row_bot1:
        st.markdown("""
        <div class="saas-card">
            <div class="saas-card-title"><span>⭐</span> Top Recommended Candidates for Role</div>
        """, unsafe_allow_html=True)
        if matches:
            for rank_idx, m in enumerate(matches[:3], start=1):
                cat = m["category"]
                b_class = "badge-strong" if cat == "Strong" else ("badge-moderate" if cat == "Moderate" else "badge-low")
                req_chips = "".join([f"<span class='skill-chip skill-chip-matched'>✓ {s}</span>" for s in m['matched_required_skills'][:4]])

                st.markdown(f"""
                <div class="applicant-item">
                    <div style="display:flex;justify-content:space-between;align-items:flex-start;">
                        <div>
                            <div style="display:flex;align-items:center;gap:8px;">
                                <span style="font-size:12px;font-weight:800;color:#4f46e5;background:#eef2ff;padding:2px 8px;border-radius:6px;">#{rank_idx}</span>
                                <strong style="font-size:16px;color:#0f172a;">{m['name']}</strong>
                                <span class="stage-pill stage-{m['status'].lower()}">{m['status']}</span>
                            </div>
                            <div style="font-size:13px;color:#64748b;margin-top:4px;">
                                📧 {m['email']} &nbsp;|&nbsp; ⏳ <strong>{m['experience_years']} yrs</strong> exp
                            </div>
                        </div>
                        <div style="text-align:right;">
                            <div style="font-size:22px;font-weight:800;color:#0f172a;">{m['overall_score']}%</div>
                            <span class="badge-match {b_class}">{cat} Fit</span>
                        </div>
                    </div>
                    <div style="margin-top:10px;">
                        <span style="font-size:12px;font-weight:600;color:#475569;">Matched Competencies:</span> {req_chips}
                    </div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("No candidates evaluated yet for this role.")
        st.markdown("</div>", unsafe_allow_html=True)

    with row_bot2:
        st.markdown("""
        <div class="saas-card">
            <div class="saas-card-title"><span>📋</span> Recent Candidate Activity</div>
        """, unsafe_allow_html=True)
        activities = get_recent_activity(5)
        if activities:
            for act in activities:
                st.markdown(f"""
                <div style="padding:10px 0;border-bottom:1px solid #f1f5f9;display:flex;justify-content:space-between;align-items:center;">
                    <div>
                        <div style="font-size:13px;font-weight:700;color:#0f172a;">{act['action']}</div>
                        <div style="font-size:12px;color:#475569;">{act['details']}</div>
                    </div>
                    <div style="font-size:11px;color:#94a3b8;white-space:nowrap;">{act['timestamp'].split(' ')[1] if ' ' in act['timestamp'] else act['timestamp']}</div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.caption("No recent activity recorded.")
        st.markdown("</div>", unsafe_allow_html=True)


# ==============================================================================
# MODULE B: JOB MANAGEMENT
# ==============================================================================
elif nav_selection == "💼 Job Management":
    st.markdown("""
    <div class="greeting-banner">
        <div>
            <span class="greeting-tag">REQUISITION WORKFLOW</span>
            <h1 class="greeting-title">Job Management</h1>
            <p class="greeting-subtitle">Define job requisitions, benchmark skill requirements, and configure target experience levels.</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

    tab_create, tab_view = st.tabs(["➕ Create New Requisition", "📋 Active Job Requisitions"])

    with tab_create:
        st.markdown("""
        <div class="saas-card">
            <div class="saas-card-title"><span>📝</span> Requisition Specifications</div>
        """, unsafe_allow_html=True)
        with st.form("create_job_form", clear_on_submit=True):
            col_j1, col_j2 = st.columns([2, 1])
            with col_j1:
                job_title = st.text_input("Job Title *", placeholder="e.g. Senior Full-Stack Python Engineer")
            with col_j2:
                job_dept = st.text_input("Department / Business Unit *", placeholder="e.g. Engineering, Product, Cloud")

            job_desc = st.text_area(
                "Job Description & Role Mission *",
                height=120,
                placeholder="Provide a comprehensive role description detailing core responsibilities, architecture stack, and deliverables..."
            )

            col_s1, col_s2, col_s3 = st.columns([2, 2, 1])
            with col_s1:
                req_skills_input = st.text_input(
                    "Required Skills (Comma separated) *",
                    placeholder="Python, Flask, SQL"
                )
            with col_s2:
                pref_skills_input = st.text_input(
                    "Preferred Skills (Comma separated)",
                    placeholder="AWS, Docker, Kubernetes, FastAPI"
                )
            with col_s3:
                min_exp_input = st.number_input(
                    "Min Experience (Yrs) *",
                    min_value=0.0,
                    max_value=25.0,
                    value=3.0,
                    step=0.5
                )

            st.markdown("<br>", unsafe_allow_html=True)
            submitted = st.form_submit_button("🚀 Publish Job Opening & Benchmark Pool", type="primary", use_container_width=True)
            if submitted:
                if not job_title or not job_dept or not job_desc or not req_skills_input:
                    st.error("Please fill in all mandatory fields (Title, Department, Description, and Required Skills).")
                else:
                    req_list = [s.strip() for s in req_skills_input.split(",") if s.strip()]
                    pref_list = [s.strip() for s in pref_skills_input.split(",") if s.strip()]

                    new_job_id = create_job(
                        title=job_title,
                        department=job_dept,
                        description=job_desc,
                        required_skills=req_list,
                        preferred_skills=pref_list,
                        min_experience=min_exp_input
                    )

                    # Auto-evaluate candidates against this new requisition
                    all_candidates = get_all_candidates()
                    new_job = get_job_by_id(new_job_id)
                    for cand in all_candidates:
                        eval_res = evaluate_candidate(new_job, cand)
                        eval_res["status"] = "New"
                        save_match_evaluation(new_job_id, cand["id"], eval_res)

                    st.session_state.active_job_id = new_job_id
                    st.success(f"Job opening '{job_title}' created successfully! Candidate pool evaluated.")
                    st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    with tab_view:
        jobs = get_all_jobs()
        if not jobs:
            st.info("No jobs defined yet.")
        else:
            for j in jobs:
                is_active = (j["id"] == st.session_state.active_job_id)
                border_color = "#3b82f6" if is_active else "#e2e8f0"
                active_badge = "<span style='background:#dbeafe;color:#1e40af;font-size:11px;font-weight:700;padding:3px 10px;border-radius:12px;'>ACTIVE BENCHMARK</span>" if is_active else ""

                req_tags = "".join([f"<span class='skill-chip skill-chip-matched'>{s}</span>" for s in j['required_skills']])
                pref_tags = "".join([f"<span class='skill-chip skill-chip-default'>{s}</span>" for s in j['preferred_skills']]) if j['preferred_skills'] else "<span style='color:#94a3b8;font-size:12px;'>None</span>"

                st.markdown(f"""
                <div class="saas-card" style="border: 2px solid {border_color};">
                    <div style="display:flex;justify-content:space-between;align-items:flex-start;">
                        <div>
                            <h3 style="margin:0;font-size:20px;color:#0f172a;">{j['title']} {active_badge}</h3>
                            <div style="font-size:13px;color:#64748b;margin-top:4px;">
                                🏢 <strong>{j['department']}</strong> &nbsp;|&nbsp; ⏳ Min Experience: <strong>{j['min_experience']} years</strong> &nbsp;|&nbsp; 📅 Created: {j['created_at']}
                            </div>
                        </div>
                    </div>
                    <p style="font-size:13.5px;color:#334155;line-height:1.6;margin:14px 0;">{j['description']}</p>
                    <div style="margin-bottom:8px;">
                        <strong style="font-size:12px;color:#0f172a;text-transform:uppercase;">Required Skills:</strong><br>{req_tags}
                    </div>
                    <div>
                        <strong style="font-size:12px;color:#0f172a;text-transform:uppercase;">Preferred Skills:</strong><br>{pref_tags}
                    </div>
                </div>
                """, unsafe_allow_html=True)

                if not is_active:
                    col_b1, col_b2 = st.columns([1.5, 4])
                    with col_b1:
                        if st.button("Set as Active Benchmark", key=f"job_active_{j['id']}", use_container_width=True):
                            st.session_state.active_job_id = j["id"]
                            st.rerun()


# ==============================================================================
# MODULE C: RESUME SCREENING
# ==============================================================================
elif nav_selection == "📄 Resume Screening":
    st.markdown("""
    <div class="greeting-banner">
        <div>
            <span class="greeting-tag">RESUME PARSING & EXTRACTION</span>
            <h1 class="greeting-title">Resume Screening</h1>
            <p class="greeting-subtitle">Batch ingest candidate PDF resumes with PyMuPDF text extraction, contact entity parsing, and automated skill scoring.</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

    if not active_job:
        st.error("Please create or select an active job requisition first.")
        st.stop()

    # Active Benchmark Reminder Box
    req_summary = ", ".join(active_job['required_skills'])
    st.markdown(f"""
    <div style="background:#f0fdf4;border:1px solid #bbf7d0;border-radius:12px;padding:16px 20px;margin-bottom:24px;display:flex;justify-content:space-between;align-items:center;">
        <div>
            <div style="font-size:12px;font-weight:700;color:#166534;text-transform:uppercase;">Screening Against Active Target</div>
            <div style="font-size:16px;font-weight:800;color:#065f46;margin-top:2px;">{active_job['title']} ({active_job['department']})</div>
            <div style="font-size:13px;color:#15803d;margin-top:2px;">Required Skills: <strong>{req_summary}</strong> &nbsp;•&nbsp; Min Exp: <strong>{active_job['min_experience']} yrs</strong></div>
        </div>
        <div>
            <span style="background:#22c55e;color:#fff;font-size:12px;font-weight:700;padding:6px 14px;border-radius:20px;">Ready for Ingestion</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Multi-file Uploader Section
    st.markdown("""
    <div class="saas-card">
        <div class="saas-card-title"><span>📥</span> Multi-File PDF Resume Uploader</div>
        <p style="font-size:13px;color:#64748b;margin-bottom:16px;">
            Drag and drop multiple applicant PDF resumes. PyMuPDF will extract full-text content, while the rule-based entity parser identifies contact information, work experience, education, and technical skill taxonomy.
        </p>
    """, unsafe_allow_html=True)

    uploaded_files = st.file_uploader(
        "Upload PDF Resumes",
        type=["pdf"],
        accept_multiple_files=True,
        help="Upload single or batch PDF resumes for automated processing."
    )

    if uploaded_files:
        st.info(f"📁 {len(uploaded_files)} file(s) queued for extraction.")

        if st.button("⚡ Start Intelligent Screening & Scoring", type="primary", use_container_width=True):
            progress_bar = st.progress(0)
            status_text = st.empty()

            processed_records = []
            error_count = 0

            for idx, uploaded_file in enumerate(uploaded_files):
                filename = uploaded_file.name
                status_text.text(f"Extracting & evaluating: {filename} ({idx+1}/{len(uploaded_files)})...")

                try:
                    file_bytes = uploaded_file.read()
                    raw_text = extract_text_from_pdf(file_bytes)
                    parsed_profile = parse_resume(raw_text, filename=filename)

                    cand_id = save_candidate(
                        name=parsed_profile["name"],
                        email=parsed_profile["email"],
                        phone=parsed_profile["phone"],
                        skills=parsed_profile["skills"],
                        experience_years=parsed_profile["experience_years"],
                        education=parsed_profile["education"],
                        projects=parsed_profile["projects"],
                        certifications=parsed_profile["certifications"],
                        resume_filename=filename,
                        raw_text=raw_text
                    )

                    all_jobs = get_all_jobs()
                    for job in all_jobs:
                        evaluation = evaluate_candidate(job, parsed_profile)
                        evaluation["status"] = "New"
                        save_match_evaluation(job["id"], cand_id, evaluation)

                    processed_records.append((parsed_profile, cand_id))
                except Exception as ex:
                    error_count += 1
                    st.error(f"Error parsing {filename}: {str(ex)}")

                progress_bar.progress((idx + 1) / len(uploaded_files))

            status_text.text("Extraction complete!")
            st.success(f"Successfully processed {len(processed_records)} applicant resume(s) into database! (Errors: {error_count})")
            log_activity("Batch Screening", f"Uploaded and analyzed {len(processed_records)} resumes.")

            # Immediate Screening Results Display
            st.markdown("<br><h4>Processed Screening Results:</h4>", unsafe_allow_html=True)
            for prof, c_id in processed_records:
                eval_for_active = evaluate_candidate(active_job, prof)
                score = eval_for_active["overall_score"]
                cat = eval_for_active["category"]
                b_class = "badge-strong" if cat == "Strong" else ("badge-moderate" if cat == "Moderate" else "badge-low")

                st.markdown(f"""
                <div class="applicant-item">
                    <div style="display:flex;justify-content:space-between;align-items:center;">
                        <div>
                            <strong style="font-size:16px;color:#0f172a;">{prof['name']}</strong>
                            <div style="font-size:13px;color:#64748b;">📧 {prof['email']} &nbsp;|&nbsp; ⏳ {prof['experience_years']} yrs experience</div>
                        </div>
                        <div style="text-align:right;">
                            <span style="font-size:22px;font-weight:800;color:#0f172a;">{score}%</span><br>
                            <span class="badge-match {b_class}">{cat} Fit</span>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)

    # Pre-Generated Sample Resumes Section
    st.markdown("""
    <div class="saas-card">
        <div class="saas-card-title"><span>📂</span> Pre-Generated Sample Resumes (Demo Suite)</div>
        <p style="font-size:13px;color:#64748b;margin-bottom:14px;">
            The system includes 6 pre-built PDF resumes in the <code>sample_resumes/</code> directory representing diverse candidates (Senior Python, Cloud Full-Stack, Junior Developer, Data Analyst, Frontend React, and Java Trainee). Download any to test live uploads:
        </p>
    """, unsafe_allow_html=True)

    sample_files = [f for f in os.listdir(SAMPLE_DIR) if f.endswith(".pdf")] if os.path.exists(SAMPLE_DIR) else []
    if sample_files:
        s_cols = st.columns(3)
        for i, sf in enumerate(sample_files):
            col_target = s_cols[i % 3]
            file_path = os.path.join(SAMPLE_DIR, sf)
            with open(file_path, "rb") as f_data:
                col_target.download_button(
                    label=f"📄 {sf}",
                    data=f_data.read(),
                    file_name=sf,
                    mime="application/pdf",
                    key=f"dl_scr_{sf}",
                    use_container_width=True
                )
    else:
        st.info("No sample files found.")
    st.markdown("</div>", unsafe_allow_html=True)


# ==============================================================================
# MODULE D, E, F: CANDIDATES DIRECTORY & PROFILES
# ==============================================================================
elif nav_selection == "👥 Candidates":
    st.markdown(f"""
    <div class="greeting-banner">
        <div>
            <span class="greeting-tag">TALENT DIRECTORY & SCORING</span>
            <h1 class="greeting-title">Candidates</h1>
            <p class="greeting-subtitle">Ranked applicant evaluation, explainable scoring criteria, and candidate dossiers for <strong>{active_job['title']}</strong>.</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

    if not active_job:
        st.error("Please create or select an active job requisition.")
        st.stop()

    matches = get_matches_for_job(active_job["id"])
    if not matches:
        st.info("No candidates evaluated yet for this position.")
        st.stop()

    # Search and Filter Bar
    st.markdown("""<div class="saas-card" style="padding:16px 20px;margin-bottom:20px;">""", unsafe_allow_html=True)
    f_c1, f_c2, f_c3, f_c4 = st.columns([1.5, 1.5, 2, 1.5])
    with f_c1:
        cat_filter = st.selectbox("Suitability Category", ["All Matches", "Strong Match (>= 70%)", "Moderate Match (45-69%)", "Low Match (< 45%)"])
    with f_c2:
        stage_filter = st.selectbox("Pipeline Stage", ["All Stages", "New", "Shortlisted", "Interview", "Offer", "Rejected"])
    with f_c3:
        min_exp_filter = st.slider("Min Experience (Years)", 0.0, 10.0, 0.0, 0.5)
    with f_c4:
        sort_choice = st.selectbox("Sort By", ["Highest Match Score", "Lowest Match Score", "Most Experience", "Candidate Name"])
    st.markdown("</div>", unsafe_allow_html=True)

    # Filter Logic
    filtered = matches[:]
    if cat_filter.startswith("Strong"):
        filtered = [m for m in filtered if m["category"] == "Strong"]
    elif cat_filter.startswith("Moderate"):
        filtered = [m for m in filtered if m["category"] == "Moderate"]
    elif cat_filter.startswith("Low"):
        filtered = [m for m in filtered if m["category"] == "Low"]

    if stage_filter != "All Stages":
        filtered = [m for m in filtered if m["status"] == stage_filter]

    filtered = [m for m in filtered if float(m["experience_years"]) >= min_exp_filter]

    # Sorting
    if sort_choice == "Highest Match Score":
        filtered.sort(key=lambda x: x["overall_score"], reverse=True)
    elif sort_choice == "Lowest Match Score":
        filtered.sort(key=lambda x: x["overall_score"])
    elif sort_choice == "Most Experience":
        filtered.sort(key=lambda x: x["experience_years"], reverse=True)
    elif sort_choice == "Candidate Name":
        filtered.sort(key=lambda x: x["name"])

    st.markdown(f"<div style='font-size:14px;font-weight:700;color:#475569;margin-bottom:16px;'>Displaying {len(filtered)} Candidate(s)</div>", unsafe_allow_html=True)

    for m in filtered:
        score = m["overall_score"]
        cat = m["category"]
        b_class = "badge-strong" if cat == "Strong" else ("badge-moderate" if cat == "Moderate" else "badge-low")
        bar_class = "score-bar-fill-strong" if cat == "Strong" else ("score-bar-fill-moderate" if cat == "Moderate" else "score-bar-fill-low")
        status = m["status"]

        with st.container():
            st.html(f"""
            <div class="applicant-item">
                <div style="display:flex;justify-content:space-between;align-items:flex-start;">
                    <div style="flex:1;">
                        <div style="display:flex;align-items:center;gap:10px;">
                            <h3 style="margin:0;font-size:18px;color:#0f172a;">{m['name']}</h3>
                            <span class="stage-pill stage-{status.lower()}">{status}</span>
                            <span class="badge-match {b_class}">{cat} Fit</span>
                        </div>
                        <div style="font-size:13px;color:#64748b;margin:4px 0 10px 0;">
                            📧 {m['email']} &nbsp;|&nbsp; 📞 {m['phone']} &nbsp;|&nbsp; ⏳ <strong>{m['experience_years']} yrs</strong> exp (Req: {active_job['min_experience']} yrs)
                        </div>
                    </div>
                    <div style="text-align:right;min-width:120px;">
                        <div style="font-size:28px;font-weight:800;color:#0f172a;line-height:1;">{score}%</div>
                        <div style="font-size:11px;font-weight:600;color:#64748b;">MATCH SCORE</div>
                        <div class="score-bar-bg" style="width:110px;margin-left:auto;">
                            <div class="{bar_class}" style="width:{min(100, int(score))}%;"></div>
                        </div>
                    </div>
                </div>

                <!-- 4-Pillar Transparent Score Explanation -->
                <div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:10px;padding:12px 16px;margin:12px 0;display:grid;grid-template-columns:repeat(4, 1fr);gap:12px;font-size:12px;">
                    <div>
                        <strong style="color:#0f172a;">1. Required Skills (40%)</strong><br>
                        <span style="font-size:15px;font-weight:700;color:#1e40af;">{m['required_match_score']} / 40</span>
                        <div style="color:#64748b;font-size:11px;">{len(m['matched_required_skills'])} of {len(active_job['required_skills'])} matched</div>
                    </div>
                    <div>
                        <strong style="color:#0f172a;">2. TF-IDF Cosine (25%)</strong><br>
                        <span style="font-size:15px;font-weight:700;color:#1e40af;">{m['tfidf_score']} / 25</span>
                        <div style="color:#64748b;font-size:11px;">Content & narrative alignment</div>
                    </div>
                    <div>
                        <strong style="color:#0f172a;">3. Preferred Skills (15%)</strong><br>
                        <span style="font-size:15px;font-weight:700;color:#1e40af;">{m['preferred_match_score']} / 15</span>
                        <div style="color:#64748b;font-size:11px;">{len(m['matched_preferred_skills'])} bonus skills matched</div>
                    </div>
                    <div>
                        <strong style="color:#0f172a;">4. Experience Fit (20%)</strong><br>
                        <span style="font-size:15px;font-weight:700;color:#1e40af;">{m['experience_score']} / 20</span>
                        <div style="color:#64748b;font-size:11px;">{m['experience_years']} yrs vs {active_job['min_experience']} yrs req.</div>
                    </div>
                </div>

                <div style="margin-top:10px;">
                    <strong style="font-size:12px;color:#334155;">Matched Skills:</strong>
                    {' '.join([f'<span class=\"skill-chip skill-chip-matched\">✓ {s}</span>' for s in m['matched_required_skills']]) if m['matched_required_skills'] else '<span style=\"color:#ef4444;font-size:12px;\">None</span>'}
                    &nbsp;&nbsp;
                    <strong style="font-size:12px;color:#334155;">Missing:</strong>
                    {' '.join([f'<span class=\"skill-chip skill-chip-missing\">✗ {s}</span>' for s in m['missing_skills']]) if m['missing_skills'] else '<span style=\"color:#10b981;font-size:12px;\">None</span>'}
                </div>
            </div>
            """)

            # Card Action Buttons
            btn_col1, btn_col2, btn_col3, btn_col4, _ = st.columns([1.5, 1.2, 1.2, 1.2, 3])
            with btn_col1:
                with st.expander("🔍 View Complete Dossier"):
                    st.markdown(f"**Education:** {m['education']}")
                    st.markdown(f"**Certifications:** {m['certifications']}")
                    st.markdown(f"**Key Projects:** {m['projects']}")
                    st.markdown("**Candidate Strengths:**")
                    for s_item in m['strengths']:
                        st.markdown(f"- <span style='color:#15803d;font-weight:500;'>{s_item}</span>", unsafe_allow_html=True)
                    st.markdown("**Areas for Recruiter Evaluation:**")
                    for a_item in m['areas_for_evaluation']:
                        st.markdown(f"- <span style='color:#b91c1c;font-weight:500;'>{a_item}</span>", unsafe_allow_html=True)
            with btn_col2:
                if status != "Shortlisted":
                    if st.button("⭐ Shortlist", key=f"sl_{m['candidate_id']}_{m['job_id']}", use_container_width=True):
                        update_candidate_status(active_job["id"], m["candidate_id"], "Shortlisted")
                        st.rerun()
            with btn_col3:
                if status != "Interview":
                    if st.button("💬 Interview", key=f"iv_{m['candidate_id']}_{m['job_id']}", use_container_width=True):
                        update_candidate_status(active_job["id"], m["candidate_id"], "Interview")
                        st.rerun()
            with btn_col4:
                if status != "Rejected":
                    if st.button("❌ Reject", key=f"rj_{m['candidate_id']}_{m['job_id']}", use_container_width=True):
                        update_candidate_status(active_job["id"], m["candidate_id"], "Rejected")
                        st.rerun()


# ==============================================================================
# MODULE G: CANDIDATE COMPARISON
# ==============================================================================
elif nav_selection == "⚖️ Candidate Comparison":
    st.markdown(f"""
    <div class="greeting-banner">
        <div>
            <span class="greeting-tag">HEAD-TO-HEAD BENCHMARKING</span>
            <h1 class="greeting-title">Candidate Comparison</h1>
            <p class="greeting-subtitle">Side-by-side competency radar analysis and qualification matrix for <strong>{active_job['title']}</strong>.</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

    if not active_job:
        st.error("Please create or select an active job requisition.")
        st.stop()

    matches = get_matches_for_job(active_job["id"])
    if len(matches) < 2:
        st.warning("Please evaluate at least 2 candidates to enable comparison.")
        st.stop()

    cand_map = {m["candidate_id"]: f"{m['name']} ({m['overall_score']}%)" for m in matches}
    default_cands = [m["candidate_id"] for m in matches[:min(3, len(matches))]]

    st.markdown("""<div class="saas-card" style="padding:18px 24px;">""", unsafe_allow_html=True)
    selected_cands = st.multiselect(
        "Select up to 3 candidates for comparative evaluation:",
        options=list(cand_map.keys()),
        default=default_cands,
        format_func=lambda x: cand_map[x],
        max_selections=3
    )
    st.markdown("</div>", unsafe_allow_html=True)

    if not selected_cands:
        st.info("Select candidates above to display comparison matrix.")
        st.stop()

    comp_data = [m for m in matches if m["candidate_id"] in selected_cands]

    # 1. Plotly Radar Chart
    st.markdown("""
    <div class="saas-card">
        <div class="saas-card-title"><span>🕸️</span> Multi-Dimensional Competency Radar</div>
    """, unsafe_allow_html=True)
    radar_metrics = ["Required Skills (40%)", "TF-IDF Relevance (25%)", "Preferred Skills (15%)", "Experience Fit (20%)", "Overall Compatibility"]

    fig_radar = go.Figure()
    palette = ["#4f46e5", "#10b981", "#f59e0b"]

    for i, rec in enumerate(comp_data):
        req_norm = (rec["required_match_score"] / 40.0) * 100
        tfidf_norm = (rec["tfidf_score"] / 25.0) * 100
        pref_norm = (rec["preferred_match_score"] / 15.0) * 100
        exp_norm = (rec["experience_score"] / 20.0) * 100
        total_norm = rec["overall_score"]

        pts = [req_norm, tfidf_norm, pref_norm, exp_norm, total_norm]
        pts.append(pts[0])

        fig_radar.add_trace(go.Scatterpolar(
            r=pts,
            theta=radar_metrics + [radar_metrics[0]],
            fill='toself',
            name=f"{rec['name']} ({rec['overall_score']}%)",
            line=dict(color=palette[i % len(palette)], width=2.5),
            opacity=0.55
        ))

    fig_radar.update_layout(
        polar=dict(
            radialaxis=dict(visible=True, range=[0, 100], gridcolor="#e2e8f0"),
            angularaxis=dict(gridcolor="#e2e8f0")
        ),
        showlegend=True,
        height=420,
        margin=dict(t=30, b=30, l=40, r=40),
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Plus Jakarta Sans, sans-serif", color="#334155")
    )
    st.plotly_chart(fig_radar, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

    # 2. Side-by-Side Comparison Columns
    st.markdown("<br><h4>Detailed Attribute Matrix</h4>", unsafe_allow_html=True)
    cols = st.columns(len(comp_data))

    for idx, rec in enumerate(comp_data):
        with cols[idx]:
            cat = rec["category"]
            b_class = "badge-strong" if cat == "Strong" else ("badge-moderate" if cat == "Moderate" else "badge-low")
            st.markdown(f"""
            <div class="saas-card" style="border-top: 4px solid {palette[idx % len(palette)]};">
                <h3 style="margin:0;font-size:18px;color:#0f172a;">{rec['name']}</h3>
                <div style="font-size:12px;color:#64748b;margin-bottom:8px;">{rec['email']}</div>
                <div style="font-size:26px;font-weight:800;color:#0f172a;">{rec['overall_score']}%</div>
                <span class="badge-match {b_class}">{cat} Fit</span> &nbsp;
                <span class="stage-pill stage-{rec['status'].lower()}">{rec['status']}</span>
                <hr style="border-color:#f1f5f9;margin:14px 0;">
                <p style="font-size:13px;color:#334155;"><strong>Experience:</strong> {rec['experience_years']} yrs (Req: {active_job['min_experience']} yrs)</p>
                <p style="font-size:13px;color:#334155;"><strong>Required Match:</strong> {rec['required_match_score']}/40</p>
                <p style="font-size:13px;color:#334155;"><strong>TF-IDF Alignment:</strong> {rec['tfidf_score']}/25</p>
                <p style="font-size:13px;color:#334155;"><strong>Preferred Match:</strong> {rec['preferred_match_score']}/15</p>
                <hr style="border-color:#f1f5f9;margin:14px 0;">
                <div style="font-size:12px;color:#0f172a;font-weight:700;margin-bottom:4px;">Matched Skills:</div>
                {' '.join([f'<span class=\"skill-chip skill-chip-matched\">✓ {s}</span>' for s in rec['matched_required_skills']]) if rec['matched_required_skills'] else '<span style=\"color:#ef4444;font-size:12px;\">None</span>'}
                <div style="font-size:12px;color:#0f172a;font-weight:700;margin:10px 0 4px 0;">Missing Skills:</div>
                {' '.join([f'<span class=\"skill-chip skill-chip-missing\">✗ {s}</span>' for s in rec['missing_skills']]) if rec['missing_skills'] else '<span style=\"color:#10b981;font-size:12px;\">None</span>'}
                <hr style="border-color:#f1f5f9;margin:14px 0;">
                <div style="font-size:12px;color:#0f172a;font-weight:700;">Education:</div>
                <div style="font-size:12px;color:#64748b;margin-top:2px;">{rec['education']}</div>
            </div>
            """, unsafe_allow_html=True)


# ==============================================================================
# MODULE H: SHORTLIST & PIPELINE
# ==============================================================================
elif nav_selection == "📋 Shortlist & Pipeline":
    st.markdown(f"""
    <div class="greeting-banner">
        <div>
            <span class="greeting-tag">APPLICANT TRACKING PIPELINE</span>
            <h1 class="greeting-title">Shortlist & Pipeline</h1>
            <p class="greeting-subtitle">Kanban workflow stages and status lifecycle management for <strong>{active_job['title']}</strong>.</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

    if not active_job:
        st.error("Please create or select an active job requisition.")
        st.stop()

    matches = get_matches_for_job(active_job["id"])

    # Pipeline Kanban Board
    stages = ["New", "Shortlisted", "Interview", "Offer", "Rejected"]
    pipe_cols = st.columns(5)

    for i, st_name in enumerate(stages):
        with pipe_cols[i]:
            stage_cands = [m for m in matches if m["status"] == st_name]
            st.markdown(f"""
            <div style="background:#ffffff;border:1px solid #e2e8f0;border-top:3px solid #4f46e5;border-radius:10px;padding:12px 14px;margin-bottom:14px;text-align:center;">
                <div style="font-size:13px;font-weight:800;color:#0f172a;">{st_name}</div>
                <div style="font-size:12px;color:#64748b;font-weight:600;">{len(stage_cands)} applicant(s)</div>
            </div>
            """, unsafe_allow_html=True)

            if not stage_cands:
                st.caption("No applicants in stage")

            for cand in stage_cands:
                score = cand["overall_score"]
                cat = cand["category"]
                b_color = "#10b981" if cat == "Strong" else ("#f59e0b" if cat == "Moderate" else "#ef4444")

                with st.container():
                    st.markdown(f"""
                    <div style="background:#ffffff;border:1px solid #e2e8f0;border-left:4px solid {b_color};border-radius:8px;padding:10px 12px;margin-bottom:10px;box-shadow:0 1px 2px rgba(0,0,0,0.03);">
                        <strong style="font-size:13.5px;color:#0f172a;">{cand['name']}</strong><br>
                        <span style="font-size:12px;color:#64748b;">Match: <strong>{score}%</strong> ({cat})</span><br>
                        <span style="font-size:11px;color:#94a3b8;">Exp: {cand['experience_years']} yrs</span>
                    </div>
                    """, unsafe_allow_html=True)

                    new_stage = st.selectbox(
                        "Move Stage:",
                        options=stages,
                        index=stages.index(st_name),
                        key=f"pipe_sel_{cand['candidate_id']}_{st_name}",
                        label_visibility="collapsed"
                    )
                    if new_stage != st_name:
                        update_candidate_status(active_job["id"], cand["candidate_id"], new_stage)
                        st.rerun()


# ==============================================================================
# MODULE: REPORTS & ANALYTICS
# ==============================================================================
elif nav_selection == "📈 Reports & Analytics":
    st.markdown(f"""
    <div class="greeting-banner">
        <div>
            <span class="greeting-tag">TALENT TELEMETRY</span>
            <h1 class="greeting-title">Reports & Analytics</h1>
            <p class="greeting-subtitle">Statistical score distributions, experience correlation, and downloadable audit reports for <strong>{active_job['title']}</strong>.</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

    if not active_job:
        st.error("Please select an active job requisition.")
        st.stop()

    matches = get_matches_for_job(active_job["id"])
    if not matches:
        st.info("No candidate telemetry available.")
        st.stop()

    # CSV Report Export Card
    csv_rows = []
    for m in matches:
        csv_rows.append({
            "Job Title": active_job["title"],
            "Candidate Name": m["name"],
            "Email": m["email"],
            "Phone": m["phone"],
            "Total Match Score (%)": m["overall_score"],
            "Category": m["category"],
            "Pipeline Status": m["status"],
            "Experience (Years)": m["experience_years"],
            "Matched Required Skills": ", ".join(m["matched_required_skills"]),
            "Missing Skills": ", ".join(m["missing_skills"]),
            "Education": m["education"],
            "Evaluated At": m["evaluated_at"]
        })
    df_export = pd.DataFrame(csv_rows)
    csv_buf = io.StringIO()
    df_export.to_csv(csv_buf, index=False)

    st.markdown("""
    <div class="saas-card" style="display:flex;justify-content:space-between;align-items:center;">
        <div>
            <h3 style="margin:0;font-size:18px;color:#0f172a;">Export Candidate Evaluation Report</h3>
            <p style="margin:4px 0 0 0;font-size:13px;color:#64748b;">Download structured CSV report containing full multi-factor score breakdown for compliance and stakeholder review.</p>
        </div>
    """, unsafe_allow_html=True)
    st.download_button(
        label="📥 Download Complete CSV Report",
        data=csv_buf.getvalue(),
        file_name=f"TalentLens_Report_{active_job['title'].replace(' ', '_')}.csv",
        mime="text/csv",
        type="primary"
    )
    st.markdown("</div>", unsafe_allow_html=True)

    # Analytics Plots Row
    r_col1, r_col2 = st.columns(2)

    with r_col1:
        st.markdown("""
        <div class="saas-card">
            <div class="saas-card-title"><span>📊</span> Experience vs. Compatibility Score</div>
        """, unsafe_allow_html=True)
        df_scatter = pd.DataFrame([{
            "Candidate": m["name"],
            "Experience": m["experience_years"],
            "Score": m["overall_score"],
            "Category": m["category"]
        } for m in matches])

        fig_scat = px.scatter(
            df_scatter,
            x="Experience",
            y="Score",
            color="Category",
            text="Candidate",
            color_discrete_map={"Strong": "#10b981", "Moderate": "#f59e0b", "Low": "#ef4444"},
            size=[14]*len(df_scatter)
        )
        fig_scat.update_traces(textposition='top center')
        fig_scat.update_layout(
            margin=dict(t=20, b=10, l=10, r=10),
            height=320,
            xaxis_title="Experience (Years)",
            yaxis_title="Match Score (%)",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(family="Plus Jakarta Sans, sans-serif", color="#334155")
        )
        st.plotly_chart(fig_scat, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

    with r_col2:
        st.markdown("""
        <div class="saas-card">
            <div class="saas-card-title"><span>📉</span> Component Score Distribution</div>
        """, unsafe_allow_html=True)
        comp_df = pd.DataFrame([{
            "Candidate": m["name"][:12],
            "Required (40)": m["required_match_score"],
            "TF-IDF (25)": m["tfidf_score"],
            "Preferred (15)": m["preferred_match_score"],
            "Experience (20)": m["experience_score"]
        } for m in matches])

        fig_stack = px.bar(
            comp_df,
            x="Candidate",
            y=["Required (40)", "TF-IDF (25)", "Preferred (15)", "Experience (20)"],
            color_discrete_sequence=["#3b82f6", "#6366f1", "#f59e0b", "#10b981"]
        )
        fig_stack.update_layout(
            margin=dict(t=20, b=10, l=10, r=10),
            height=320,
            xaxis_title="",
            yaxis_title="Points",
            barmode='stack',
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(family="Plus Jakarta Sans, sans-serif", color="#334155")
        )
        st.plotly_chart(fig_stack, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)


# ==============================================================================
# MODULE: SETTINGS & DEMO MANAGEMENT
# ==============================================================================
elif nav_selection == "⚙️ Settings":
    st.markdown("""
    <div class="greeting-banner">
        <div>
            <span class="greeting-tag">SYSTEM & DATA CONFIGURATION</span>
            <h1 class="greeting-title">Settings & Demo Suite</h1>
            <p class="greeting-subtitle">Manage persistence, review engine specifications, and reset demo data for presentations.</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="saas-card">
        <div class="saas-card-title"><span>⚙️</span> Engine Architecture & Privacy Assurance</div>
        <p style="font-size:13.5px;color:#334155;line-height:1.6;">
            <strong>Deterministic Classical NLP:</strong> TalentLens runs completely locally on your workstation using Scikit-Learn TF-IDF vector space modeling, PyMuPDF native C-bindings, and embedded SQLite. Zero personal applicant data is ever sent to external cloud APIs, LLM providers, or paid third-party platforms.
        </p>
    </div>
    """, unsafe_allow_html=True)

    with st.expander("🔄 Reset Presentation Demo Data", expanded=True):
        st.warning("Resetting drops custom jobs and candidates, re-seeding the verified college presentation dataset with 6 synthetic applicants and the benchmark Python Developer requisition.")
        chk_confirm = st.checkbox("I confirm I want to reset and re-seed demo data")
        if st.button("Re-Seed Presentation Dataset", type="primary", disabled=not chk_confirm):
            reset_database()
            generate_all_samples()
            jobs = get_all_jobs()
            if jobs:
                st.session_state.active_job_id = jobs[0]["id"]
            st.success("Database successfully reset and re-seeded with presentation samples!")
            st.rerun()

st.markdown("<br><hr style='border-color:#e2e8f0;'>", unsafe_allow_html=True)
st.markdown("<div style='text-align:center;font-size:12px;color:#94a3b8;'>TalentLens Enterprise Suite • Deterministic Explainable Recruitment AI • Local & Secure</div>", unsafe_allow_html=True)
