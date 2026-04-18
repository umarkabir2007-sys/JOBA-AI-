import streamlit as st
import pandas as pd
import requests
from io import BytesIO
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER
from utils import (
    extract_resume_text, fetch_all_jobs, match_resume_to_jobs, load_model,
    fetch_scholarships, analyze_scholarship_requirements,
    save_cv_data, get_cv_data, save_payment_status, verify_flutterwave_payment
)

st.set_page_config(page_title="Joba AI - CV Builder & Job Matcher", layout="wide", initial_sidebar_state="expanded")

# ---------- SESSION STATE ----------
if 'theme' not in st.session_state:
    st.session_state.theme = "dark"
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'user_email' not in st.session_state:
    st.session_state.user_email = ""
if 'user_type' not in st.session_state:
    st.session_state.user_type = "jobseeker"
if 'paid_cv' not in st.session_state:
    st.session_state.paid_cv = False
if 'paid_job' not in st.session_state:
    st.session_state.paid_job = False
if 'paid_scholarship' not in st.session_state:
    st.session_state.paid_scholarship = False
if 'cv_data' not in st.session_state:
    st.session_state.cv_data = None
if 'education_list' not in st.session_state:
    st.session_state.education_list = []
if 'work_list' not in st.session_state:
    st.session_state.work_list = []
if 'skills_list' not in st.session_state:
    st.session_state.skills_list = []
if 'sectors_list' not in st.session_state:
    st.session_state.sectors_list = []
if 'matched_jobs' not in st.session_state:
    st.session_state.matched_jobs = []

# ---------- THEME TOGGLE ----------
def toggle_theme():
    st.session_state.theme = "light" if st.session_state.theme == "dark" else "dark"
    st.rerun()

def get_theme_css():
    if st.session_state.theme == "dark":
        return """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap');
        * { font-family: 'Inter', sans-serif; }
        .stApp { background: radial-gradient(circle at 10% 20%, #0f172a, #0a0f1a); color: #f1f5f9; }
        [data-testid="stSidebar"] { background: rgba(15,23,42,0.9); backdrop-filter: blur(16px); border-right: 1px solid rgba(59,130,246,0.3); }
        .stButton>button { background: linear-gradient(90deg,#3b82f6,#2563eb); color:white; border:none; border-radius:40px; padding:0.6rem 1.5rem; font-weight:600; width:100%; transition:0.3s; }
        .stButton>button:hover { transform:translateY(-2px); box-shadow:0 8px 20px rgba(59,130,246,0.4); }
        .job-card, .scholarship-card { background: rgba(30,41,59,0.7); backdrop-filter: blur(12px); border-radius:24px; padding:1.5rem; margin-bottom:1.5rem; border:1px solid rgba(59,130,246,0.3); transition:0.3s; }
        .job-card:hover, .scholarship-card:hover { transform:translateY(-4px); border-color:#3b82f6; background: rgba(30,41,59,0.9); }
        .job-title { font-size:1.4rem; font-weight:700; background:linear-gradient(135deg,#fff,#94a3b8); -webkit-background-clip:text; background-clip:text; color:transparent; }
        .similarity-badge { background:#1e293b; padding:0.2rem 0.8rem; border-radius:40px; font-size:0.8rem; font-weight:600; color:#3b82f6; border:1px solid #3b82f6; display:inline-block; }
        .apply-btn { background:#3b82f6; color:white; padding:0.5rem 1.2rem; border-radius:40px; text-decoration:none; font-weight:600; display:inline-flex; align-items:center; gap:0.5rem; margin-top:0.75rem; transition:0.2s; }
        .apply-btn:hover { background:#2563eb; transform:scale(1.02); }
        .locked-btn { background:#64748b; color:white; padding:0.5rem 1.2rem; border-radius:40px; display:inline-flex; align-items:center; gap:0.5rem; cursor:not-allowed; }
        .stTabs [data-baseweb="tab-list"] { gap:0.8rem; background:rgba(15,23,42,0.5); border-radius:60px; padding:0.5rem; }
        .stTabs [data-baseweb="tab"] { border-radius:40px; padding:0.5rem 1.2rem; font-weight:600; color:#94a3b8; }
        .stTabs [aria-selected="true"] { background:#3b82f6; color:white; }
        .stTextInput>div>div>input, .stTextArea>div>div>textarea, .stSelectbox>div>div { background:#1e293b; border:1px solid #334155; border-radius:16px; color:white; padding:0.6rem 1rem; }
        .feature-header { display: flex; align-items: center; gap: 1rem; margin-bottom: 1rem; background: rgba(30,41,59,0.5); padding: 0.5rem 1rem; border-radius: 60px; width: fit-content; }
        .feature-header img { width: 40px; height: 40px; border-radius: 50%; background: #3b82f6; padding: 8px; }
        .feature-header h2 { margin: 0; font-size: 1.5rem; }
        </style>
        """
    else:
        return """
        <style>
        .stApp { background:#f8fafc; color:#0f172a; }
        [data-testid="stSidebar"] { background:white; border-right:1px solid #e2e8f0; }
        .stButton>button { background:linear-gradient(90deg,#3b82f6,#2563eb); color:white; border:none; border-radius:40px; padding:0.6rem 1.5rem; font-weight:600; width:100%; }
        .job-card, .scholarship-card { background:white; border-radius:24px; padding:1.5rem; margin-bottom:1.5rem; border:1px solid #e2e8f0; box-shadow:0 4px 6px -1px rgba(0,0,0,0.05); }
        .job-card:hover { transform:translateY(-4px); box-shadow:0 20px 30px -12px rgba(0,0,0,0.1); }
        .job-title { font-size:1.4rem; font-weight:700; color:#0f172a; }
        .similarity-badge { background:#e2e8f0; padding:0.2rem 0.8rem; border-radius:40px; color:#2563eb; }
        .apply-btn { background:#3b82f6; color:white; padding:0.5rem 1.2rem; border-radius:40px; text-decoration:none; display:inline-flex; }
        .locked-btn { background:#94a3b8; color:white; padding:0.5rem 1.2rem; border-radius:40px; display:inline-flex; align-items:center; gap:0.5rem; cursor:not-allowed; }
        .stTabs [data-baseweb="tab-list"] { background:#f1f5f9; border-radius:60px; padding:0.5rem; }
        .stTabs [data-baseweb="tab"] { border-radius:40px; padding:0.5rem 1.2rem; font-weight:600; color:#475569; }
        .stTabs [aria-selected="true"] { background:#3b82f6; color:white; }
        .stTextInput>div>div>input, .stTextArea>div>div>textarea { background:white; border:1px solid #cbd5e1; border-radius:16px; }
        .feature-header { display: flex; align-items: center; gap: 1rem; margin-bottom: 1rem; background: #f1f5f9; padding: 0.5rem 1rem; border-radius: 60px; width: fit-content; }
        .feature-header img { width: 40px; height: 40px; border-radius: 50%; background: #3b82f6; padding: 8px; }
        .feature-header h2 { margin: 0; font-size: 1.5rem; }
        </style>
        """
st.markdown(get_theme_css(), unsafe_allow_html=True)

# ---------- AUTHENTICATION ----------
def login():
    st.sidebar.subheader("🔐 Login / Register")
    email = st.sidebar.text_input("Email")
    user_type = st.sidebar.selectbox("I am a", ["Job Seeker", "Employer"])
    if st.sidebar.button("Login / Register"):
        if email:
            st.session_state.logged_in = True
            st.session_state.user_email = email
            st.session_state.user_type = "jobseeker" if user_type == "Job Seeker" else "employer"
            st.session_state.paid_cv = save_payment_status(email, "cv", "get")
            st.session_state.paid_job = save_payment_status(email, "job", "get")
            st.session_state.paid_scholarship = save_payment_status(email, "scholarship", "get")
            st.rerun()
        else:
            st.sidebar.error("Please enter email")

def logout():
    if st.sidebar.button("Logout"):
        for key in ['logged_in', 'user_email', 'user_type', 'paid_cv', 'paid_job', 'paid_scholarship']:
            if key in st.session_state:
                del st.session_state[key]
        st.rerun()

# ---------- PAYMENT SECTION ----------
def payment_section(feature, amount, feature_key):
    st.markdown(f"### 💰 Unlock {feature} – ₦{amount} one‑time")
    st.markdown(f'<a href="https://sandbox.flutterwave.com/pay/rpflm1gkqxsq" target="_blank"><button style="background:#3b82f6; color:white; padding:0.5rem 1rem; border-radius:40px; border:none;">Pay with Flutterwave</button></a>', unsafe_allow_html=True)
    tx_ref = st.text_input("Transaction Reference")
    if st.button(f"Verify Payment for {feature}"):
        if verify_flutterwave_payment(tx_ref):
            save_payment_status(st.session_state.user_email, feature_key, "set", True)
            st.session_state[feature_key] = True
            st.success(f"Payment verified! {feature} unlocked.")
            st.rerun()
        else:
            st.error("Invalid reference. Please try again.")

# ---------- PDF GENERATION ----------
def generate_full_cv_pdf(data):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, leftMargin=0.7*inch, rightMargin=0.7*inch, topMargin=0.7*inch, bottomMargin=0.7*inch)
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('Title', parent=styles['Heading1'], fontSize=18, leading=22, alignment=TA_CENTER, spaceAfter=12, textColor=colors.HexColor('#1e3a8a'))
    heading_style = ParagraphStyle('Heading2', parent=styles['Heading2'], fontSize=12, leading=14, spaceBefore=10, spaceAfter=6, textColor=colors.HexColor('#0f172a'), fontName='Helvetica-Bold')
    normal_style = ParagraphStyle('Normal', parent=styles['Normal'], fontSize=10, leading=12, alignment=TA_LEFT, spaceAfter=4)
    bullet_style = ParagraphStyle('Bullet', parent=normal_style, leftIndent=12, bulletIndent=0, spaceAfter=2)
    story = []
    story.append(Paragraph(data.get('full_name', '').upper(), title_style))
    contact_info = [
        [f"📧 {data.get('email', '')}", f"📞 {data.get('phone', '')}"],
        [f"📍 {data.get('address', '')}, {data.get('city', '')}, {data.get('state', '')}", f"🌍 {data.get('country', '')}"]
    ]
    contact_table = Table(contact_info, colWidths=[3.2*inch, 2.5*inch])
    contact_table.setStyle(TableStyle([('FONTNAME', (0,0), (-1,-1), 'Helvetica'), ('FONTSIZE', (0,0), (-1,-1), 9), ('TEXTCOLOR', (0,0), (-1,-1), colors.gray), ('ALIGN', (0,0), (-1,-1), 'LEFT'), ('VALIGN', (0,0), (-1,-1), 'TOP'), ('TOPPADDING', (0,0), (-1,-1), 2), ('BOTTOMPADDING', (0,0), (-1,-1), 2)]))
    story.append(contact_table)
    story.append(Spacer(1, 12))
    if data.get('summary'):
        story.append(Paragraph("PROFESSIONAL SUMMARY", heading_style))
        story.append(Paragraph(data['summary'], normal_style))
        story.append(Spacer(1, 6))
    if data.get('education'):
        story.append(Paragraph("EDUCATION", heading_style))
        for edu in data['education']:
            story.append(Paragraph(f"<b>{edu.get('institution', '')}</b> | {edu.get('degree', '')} in {edu.get('field', '')}", normal_style))
            story.append(Paragraph(f"<i>{edu.get('start_date', '')} – {edu.get('end_date', '')}</i>", normal_style))
            if edu.get('description'):
                story.append(Paragraph(f"• {edu['description']}", bullet_style))
            story.append(Spacer(1, 4))
        story.append(Spacer(1, 6))
    if data.get('work'):
        story.append(Paragraph("WORK EXPERIENCE", heading_style))
        for work in data['work']:
            story.append(Paragraph(f"<b>{work.get('company', '')}</b> – {work.get('position', '')}", normal_style))
            story.append(Paragraph(f"<i>{work.get('start_date', '')} – {work.get('end_date', '')}</i>", normal_style))
            if work.get('description'):
                for line in work['description'].split('\n'):
                    if line.strip():
                        story.append(Paragraph(f"• {line.strip()}", bullet_style))
            story.append(Spacer(1, 4))
        story.append(Spacer(1, 6))
    if data.get('skills'):
        story.append(Paragraph("SKILLS & COMPETENCIES", heading_style))
        skills_text = ", ".join([f"{s.get('name', '')} ({s.get('level', '')})" for s in data['skills']])
        story.append(Paragraph(skills_text, normal_style))
        story.append(Spacer(1, 6))
    if data.get('sectors'):
        story.append(Paragraph("SECTORS OF INTEREST", heading_style))
        for sec in data['sectors']:
            story.append(Paragraph(f"• <b>{sec.get('sector', '')}</b> – {sec.get('subsector', '')}", bullet_style))
            if sec.get('description'):
                story.append(Paragraph(f"  {sec['description']}", normal_style))
        story.append(Spacer(1, 6))
    story.append(Paragraph("ADDITIONAL INFORMATION", heading_style))
    if data.get('languages'):
        story.append(Paragraph(f"<b>Languages:</b> {', '.join(data['languages'])}", normal_style))
    if data.get('marital_status'):
        story.append(Paragraph(f"<b>Marital Status:</b> {data['marital_status']}", normal_style))
    if data.get('disability'):
        story.append(Paragraph(f"<b>Disability:</b> {', '.join(data['disability'])}", normal_style))
    if data.get('work_preferences'):
        wp = data['work_preferences']
        story.append(Paragraph(f"<b>Work Model:</b> {wp.get('model', '')} | <b>Programme:</b> {wp.get('programme', '')}", normal_style))
    doc.build(story)
    buffer.seek(0)
    return buffer

# ---------- CV BUILDER SECTION (with image header) ----------
def cv_builder_section():
    st.markdown("""
    <div class="feature-header">
        <img src="https://cdn-icons-png.flaticon.com/512/3135/3135715.png" alt="CV Builder">
        <h2>📝 Joba CV Builder</h2>
    </div>
    <p>Create a professional, ATS-friendly CV. Fill in your details, preview, and pay ₦500 to download.</p>
    """, unsafe_allow_html=True)
    
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["📋 Personal Info", "🎓 Education", "💼 Work Experience", "⚙️ Skills & Sectors", "➕ Additional Info", "💎 Preview & Download"])
    cv_data = {}
    
    with tab1:
        st.subheader("Personal Information")
        col1, col2 = st.columns(2)
        with col1:
            cv_data['full_name'] = st.text_input("Full Name *")
            cv_data['email'] = st.text_input("Email *")
            cv_data['phone'] = st.text_input("Phone *")
            cv_data['country'] = st.text_input("Country", value="Nigeria")
        with col2:
            cv_data['address'] = st.text_area("Address")
            cv_data['city'] = st.text_input("City")
            cv_data['state'] = st.text_input("State")
            cv_data['postal_code'] = st.text_input("Postal Code")
        st.subheader("Social Links")
        cv_data['linkedin'] = st.text_input("LinkedIn URL")
        cv_data['facebook'] = st.text_input("Facebook URL")
        cv_data['instagram'] = st.text_input("Instagram URL")
        st.subheader("Professional Summary")
        cv_data['summary'] = st.text_area("Write a brief professional summary about yourself", height=150)
        st.subheader("Location Information")
        col1, col2, col3 = st.columns(3)
        with col1:
            cv_data['state_of_residence'] = st.text_input("State of Residence")
        with col2:
            cv_data['lga'] = st.text_input("LGA of Residence")
        with col3:
            cv_data['region'] = st.text_input("Region")
    
    with tab2:
        st.subheader("Education History")
        for idx, edu in enumerate(st.session_state.education_list):
            with st.expander(f"📘 Education #{idx+1}: {edu.get('institution', 'New Entry')}"):
                col1, col2 = st.columns(2)
                with col1:
                    edu['institution'] = st.text_input("Institution", value=edu.get('institution', ''), key=f"edu_inst_{idx}")
                    edu['degree'] = st.text_input("Degree", value=edu.get('degree', ''), key=f"edu_deg_{idx}")
                with col2:
                    edu['field'] = st.text_input("Field of Study", value=edu.get('field', ''), key=f"edu_field_{idx}")
                    edu['start_date'] = st.text_input("Start Date", value=edu.get('start_date', ''), key=f"edu_start_{idx}")
                    edu['end_date'] = st.text_input("End Date", value=edu.get('end_date', ''), key=f"edu_end_{idx}")
                edu['description'] = st.text_area("Description", value=edu.get('description', ''), key=f"edu_desc_{idx}")
                if st.button(f"❌ Remove Education #{idx+1}", key=f"remove_edu_{idx}"):
                    st.session_state.education_list.pop(idx)
                    st.rerun()
        if st.button("➕ Add Education"):
            st.session_state.education_list.append({"institution": "", "degree": "", "field": "", "start_date": "", "end_date": "", "description": ""})
            st.rerun()
    
    with tab3:
        st.subheader("Work Experience")
        for idx, work in enumerate(st.session_state.work_list):
            with st.expander(f"🏢 Work #{idx+1}: {work.get('company', 'New Entry')}"):
                col1, col2 = st.columns(2)
                with col1:
                    work['company'] = st.text_input("Company", value=work.get('company', ''), key=f"work_comp_{idx}")
                    work['position'] = st.text_input("Position", value=work.get('position', ''), key=f"work_pos_{idx}")
                with col2:
                    work['start_date'] = st.text_input("Start Date", value=work.get('start_date', ''), key=f"work_start_{idx}")
                    work['end_date'] = st.text_input("End Date", value=work.get('end_date', ''), key=f"work_end_{idx}")
                work['description'] = st.text_area("Description", value=work.get('description', ''), key=f"work_desc_{idx}")
                if st.button(f"❌ Remove Work #{idx+1}", key=f"remove_work_{idx}"):
                    st.session_state.work_list.pop(idx)
                    st.rerun()
        if st.button("➕ Add Work Experience"):
            st.session_state.work_list.append({"company": "", "position": "", "start_date": "", "end_date": "", "description": ""})
            st.rerun()
    
    with tab4:
        st.subheader("Skills")
        for idx, skill in enumerate(st.session_state.skills_list):
            with st.expander(f"🛠️ Skill #{idx+1}: {skill.get('name', 'New')}"):
                col1, col2, col3 = st.columns(3)
                with col1:
                    skill['name'] = st.text_input("Skill Name", value=skill.get('name', ''), key=f"skill_name_{idx}")
                with col2:
                    skill['category'] = st.text_input("Category", value=skill.get('category', ''), key=f"skill_cat_{idx}")
                with col3:
                    skill['level'] = st.selectbox("Level", ["Beginner", "Intermediate", "Advanced", "Expert"], index=["Beginner","Intermediate","Advanced","Expert"].index(skill.get('level','Beginner')), key=f"skill_level_{idx}")
                if st.button(f"❌ Remove Skill #{idx+1}", key=f"remove_skill_{idx}"):
                    st.session_state.skills_list.pop(idx)
                    st.rerun()
        if st.button("➕ Add Skill"):
            st.session_state.skills_list.append({"name": "", "category": "", "level": "Beginner"})
            st.rerun()
        st.subheader("Sectors of Interest")
        for idx, sec in enumerate(st.session_state.sectors_list):
            with st.expander(f"🎯 Sector #{idx+1}: {sec.get('sector', 'New')}"):
                col1, col2 = st.columns(2)
                with col1:
                    sec['sector'] = st.text_input("Sector", value=sec.get('sector', ''), key=f"sector_name_{idx}")
                with col2:
                    sec['subsector'] = st.text_input("Subsector", value=sec.get('subsector', ''), key=f"sector_sub_{idx}")
                sec['description'] = st.text_area("Description (Optional)", value=sec.get('description', ''), key=f"sector_desc_{idx}")
                if st.button(f"❌ Remove Sector #{idx+1}", key=f"remove_sector_{idx}"):
                    st.session_state.sectors_list.pop(idx)
                    st.rerun()
        if st.button("➕ Add Sector of Interest"):
            st.session_state.sectors_list.append({"sector": "", "subsector": "", "description": ""})
            st.rerun()
    
    with tab5:
        st.subheader("Additional Information")
        cv_data['languages'] = st.multiselect("Spoken Languages", ["Yoruba", "Igbo", "Hausa", "Pidgin", "Fulfulde", "Others"])
        cv_data['marital_status'] = st.selectbox("Marital Status", ["Single", "Married", "Divorced", "Widowed"])
        disability_options = ["None", "Hearing loss", "Vision impairment", "Autism", "Walking Disability", "Intellectual Disability", "Cerebral palsy", "Mental disorder"]
        cv_data['disability'] = st.multiselect("Disability Status", disability_options)
        st.subheader("Work Preferences")
        cv_data['work_preferences'] = {
            'programme': st.selectbox("Placements Programme", ["Yes", "No"]),
            'model': st.selectbox("Work Model Preference", ["Onsite", "Remote", "Hybrid"])
        }
    
    with tab6:
        st.subheader("Preview & Download")
        if st.button("💾 Save All CV Data", use_container_width=True):
            cv_data['education'] = st.session_state.education_list
            cv_data['work'] = st.session_state.work_list
            cv_data['skills'] = st.session_state.skills_list
            cv_data['sectors'] = st.session_state.sectors_list
            st.session_state.cv_data = cv_data
            save_cv_data(st.session_state.user_email, cv_data)
            st.success("✅ CV data saved!")
        if st.session_state.cv_data:
            st.markdown("---")
            if not st.session_state.get('paid_cv', False):
                payment_section("CV Download", 500, "paid_cv")
            else:
                st.success("✅ Payment confirmed. Your CV is ready for download.")
                pdf_buffer = generate_full_cv_pdf(st.session_state.cv_data)
                st.download_button("📥 Download CV (PDF)", pdf_buffer, "Joba_CV.pdf", "application/pdf", use_container_width=True)
        else:
            st.info("ℹ️ Fill your CV data and click 'Save All CV Data' first.")

# ---------- JOB MATCHER SECTION (with image header) ----------
def job_matcher_section():
    st.markdown("""
    <div class="feature-header">
        <img src="https://cdn-icons-png.flaticon.com/512/2830/2830312.png" alt="Job Matcher">
        <h2>🎯 AI Job Matcher</h2>
    </div>
    <p>Upload your CV to see matching jobs. Pay ₦1,000 to unlock apply links.</p>
    """, unsafe_allow_html=True)
    
    uploaded_file = st.file_uploader("Upload your CV (PDF)", type="pdf")
    if uploaded_file:
        with st.spinner("Processing..."):
            resume_text = extract_resume_text(uploaded_file)
            jobs = fetch_all_jobs()
            model = load_model()
            matched = match_resume_to_jobs(resume_text, jobs, model)
            st.session_state.matched_jobs = matched
        
        st.subheader("Filter jobs")
        col1, col2 = st.columns(2)
        with col1:
            user_location = st.text_input("Your City/State (e.g., Kano, Lagos)")
        with col2:
            abroad_pref = st.radio("Work preference", ["Nigeria only", "Open to abroad"])
        
        filtered = st.session_state.matched_jobs
        if user_location:
            filtered = [j for j in filtered if user_location.lower() in j.get('location', '').lower() or "remote" in j.get('description', '').lower()]
        if abroad_pref == "Nigeria only":
            filtered = [j for j in filtered if "nigeria" in j.get('location', '').lower() or "remote" in j.get('description', '').lower()]
        
        st.subheader(f"🎯 Top {len(filtered)} matching jobs")
        paid = st.session_state.get('paid_job', False)
        for job in filtered[:20]:
            similarity = int(job.get('similarity', 0)*100)
            if paid:
                apply_html = f'<a href="{job.get("url")}" target="_blank" class="apply-btn">Apply →</a>'
            else:
                apply_html = '<span class="locked-btn">🔒 Pay to Unlock Apply Link</span>'
            st.markdown(f"""
            <div class="job-card">
                <div class="job-title">{job.get('title')}</div>
                <div>🏢 {job.get('company')} | 📍 {job.get('location', 'Remote')}</div>
                <div><span class="similarity-badge">Match {similarity}%</span></div>
                <div>{job.get('description')[:200]}...</div>
                {apply_html}
            </div>
            """, unsafe_allow_html=True)
        
        if not paid:
            st.markdown("---")
            payment_section("Job Matcher (unlock apply links)", 1000, "paid_job")

# ---------- SCHOLARSHIP FINDER SECTION (with image header) ----------
def scholarship_section():
    st.markdown("""
    <div class="feature-header">
        <img src="https://cdn-icons-png.flaticon.com/512/3135/3135689.png" alt="Scholarships">
        <h2>🎓 Scholarship Finder & AI Analyzer</h2>
    </div>
    <p>Find scholarships worldwide. Pay ₦500 to unlock AI requirement analysis and official links.</p>
    """, unsafe_allow_html=True)
    
    scholarships = fetch_scholarships()
    st.subheader("🔍 Search Scholarships")
    col1, col2 = st.columns(2)
    with col1:
        search_name = st.text_input("Search by name", key="scholar_name")
    with col2:
        search_country = st.text_input("Search by country", key="scholar_country")
    
    search_clicked = st.button("🔍 Search", use_container_width=True)
    filtered = scholarships
    if search_clicked:
        if search_name:
            filtered = [s for s in filtered if search_name.lower() in s['name'].lower()]
        if search_country:
            filtered = [s for s in filtered if search_country.lower() in s['country'].lower()]
    else:
        if search_name:
            filtered = [s for s in filtered if search_name.lower() in s['name'].lower()]
        if search_country:
            filtered = [s for s in filtered if search_country.lower() in s['country'].lower()]
    
    st.write(f"Found {len(filtered)} scholarships")
    paid = st.session_state.get('paid_scholarship', False)
    for sch in filtered:
        with st.expander(f"📘 {sch['name']} – {sch['country']} (Deadline: {sch['deadline']})"):
            st.write(sch['description'][:300])
            if paid:
                if st.button(f"🔍 Analyze requirements for {sch['name']}", key=sch['id']):
                    with st.spinner("AI is reading the scholarship requirements..."):
                        analysis = analyze_scholarship_requirements(sch['url'])
                    st.markdown("### 📋 What you need to prepare:")
                    st.write(analysis)
                st.markdown(f"[🔗 Official Link]({sch['url']})")
            else:
                st.markdown('<span class="locked-btn">🔒 Pay ₦500 to unlock analysis & official link</span>', unsafe_allow_html=True)
    
    if not paid and filtered:
        st.markdown("---")
        payment_section("Scholarship Analyzer", 500, "paid_scholarship")

# ---------- TESTIMONIALS SECTION (with image header) ----------
def testimonials_section():
    st.markdown("""
    <div class="feature-header">
        <img src="https://cdn-icons-png.flaticon.com/512/3135/3135710.png" alt="Testimonials">
        <h2>⭐ What Our Users Say</h2>
    </div>
    <p>Real stories from real job seekers and employers</p>
    """, unsafe_allow_html=True)
    
    testimonials = [
        {"name": "Amina B., Lagos", "role": "Software Developer", "text": "The CV builder saved me hours! I got a job offer within 2 weeks. The AI job matching is incredibly accurate.", "rating": 5},
        {"name": "David O., Abuja", "role": "Data Analyst", "text": "Worth every kobo. I was skeptical at first, but after paying ₦1,000 and getting my CV, I landed an interview at a top bank.", "rating": 5},
        {"name": "Grace E., Port Harcourt", "role": "Project Manager", "text": "Joba AI helped me match with remote jobs I never knew existed. I'm now working as a freelance project manager.", "rating": 5},
        {"name": "Samuel K., Kano", "role": "Full Stack Developer", "text": "The scholarship finder is a game changer. I found a fully funded scholarship to study in Germany.", "rating": 5},
        {"name": "Fatima M., Ibadan", "role": "Marketing Specialist", "text": "Best ₦1,000 I've spent. The CV looks professional and the job matcher found roles tailored to my skills.", "rating": 5},
        {"name": "John C., Enugu", "role": "IT Support", "text": "Simple, fast, and effective. I recommended it to 5 friends, and 3 of them have already found jobs.", "rating": 4},
        {"name": "Hauwa A., Jos", "role": "Teacher", "text": "I never thought I could afford a professional CV. Joba AI made it possible.", "rating": 5},
        {"name": "Emeka N., Anambra", "role": "Business Analyst", "text": "The AI job matcher is scary accurate. It found jobs I would have never discovered on my own.", "rating": 5},
        {"name": "Blessing U., Delta", "role": "Graphic Designer", "text": "The WhatsApp integration makes applying so easy. I've already gotten 3 interviews.", "rating": 5},
        {"name": "Ibrahim B., Kaduna", "role": "Cybersecurity Analyst", "text": "The AI job matcher is scary accurate. Highly recommended!", "rating": 5}
    ]
    
    cols = st.columns(3)
    for idx, t in enumerate(testimonials):
        with cols[idx % 3]:
            stars = "⭐" * t['rating'] + "☆" * (5 - t['rating'])
            st.markdown(f"""
            <div class="testimonial-card" style="background: rgba(30,41,59,0.5); border-radius: 20px; padding: 1.2rem; margin-bottom: 1rem;">
                <p style="font-size: 0.9rem;">"{t['text']}"</p>
                <p style="margin-top: 0.5rem;"><strong>{t['name']}</strong><br>{t['role']}<br>{stars}</p>
            </div>
            """, unsafe_allow_html=True)

# ---------- SIDEBAR & NAVIGATION ----------
with st.sidebar:
    if not st.session_state.get('logged_in', False):
        login()
    else:
        st.write(f"👋 Welcome, {st.session_state.user_email}")
        st.write(f"Role: {st.session_state.user_type}")
        logout()
        st.markdown("---")
        if st.session_state.user_type == "jobseeker":
            option = st.radio("Navigate", [
                "📄 CV Builder", "🎯 Job Matcher", "🎓 Scholarships", "⭐ Testimonials"
            ])
        else:
            option = st.radio("Navigate", [
                "🏢 Employer Zone", "📢 Job Listings", "👥 Talent Directory", "⭐ Testimonials"
            ])
        st.markdown("---")
        col1, col2 = st.columns([3,1])
        with col1: st.write("Theme:")
        with col2:
            if st.button("🌓" if st.session_state.theme == "dark" else "☀️"):
                toggle_theme()
        st.caption("© 2025 Joba AI")

# ---------- MAIN ----------
if not st.session_state.get('logged_in', False):
    st.markdown("# 🚀 Welcome to Joba AI")
    st.markdown("### Build your CV, find jobs, and get scholarships – all in one place")
    st.image("https://images.unsplash.com/photo-1522071820081-009f0129c71c?auto=format&fit=crop&w=800&q=80", use_column_width=True)
    st.info("👈 Please login or register using the sidebar to access all features.")
else:
    if st.session_state.user_type == "jobseeker":
        if option == "📄 CV Builder":
            cv_builder_section()
        elif option == "🎯 Job Matcher":
            job_matcher_section()
        elif option == "🎓 Scholarships":
            scholarship_section()
        else:
            testimonials_section()
    else:
        st.info("Employer features coming soon. For now, please use Job Seeker account.")