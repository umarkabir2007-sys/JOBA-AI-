import pandas as pd
import requests
import json
import os
import re
from io import BytesIO
from datetime import datetime
from bs4 import BeautifulSoup
from pdfminer.high_level import extract_text
from nltk.corpus import stopwords
from nltk.stem import PorterStemmer
import nltk
import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import streamlit as st

# Download NLTK data
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')
try:
    nltk.data.find('corpora/stopwords')
except LookupError:
    nltk.download('stopwords')

stemmer = PorterStemmer()
stop_words = set(stopwords.words('english'))

@st.cache_resource
def load_model():
    return SentenceTransformer('all-MiniLM-L6-v2')

def extract_resume_text(pdf_file) -> str:
    text = extract_text(BytesIO(pdf_file.getvalue()))
    return text.strip()

def preprocess_text(text: str) -> str:
    text = re.sub(r'[^a-zA-Z\s]', '', text.lower())
    tokens = text.split()
    tokens = [stemmer.stem(word) for word in tokens if word not in stop_words]
    return ' '.join(tokens)

def compute_similarity(resume_embedding, job_embeddings):
    resume_2d = np.atleast_2d(resume_embedding)
    jobs_2d = np.atleast_2d(job_embeddings)
    if jobs_2d.ndim == 1:
        jobs_2d = jobs_2d.reshape(1, -1)
    return cosine_similarity(resume_2d, jobs_2d)[0]

def fetch_remoteok_jobs():
    try:
        resp = requests.get("https://remoteok.com/api", timeout=10)
        resp.raise_for_status()
        data = resp.json()
        jobs = []
        for job in data[1:]:
            jobs.append({
                'title': job.get('position', ''),
                'company': job.get('company', ''),
                'description': job.get('description', ''),
                'url': job.get('url', ''),
                'location': job.get('location', 'Remote')
            })
        return jobs
    except Exception:
        return []

def fetch_microsoft_jobs(): return []
def fetch_angellist_jobs(): return []

def load_csv_fallback(csv_path='jobs.csv'):
    df = pd.read_csv(csv_path)
    return df.to_dict('records')

def fetch_all_jobs(csv_path='jobs.csv'):
    jobs = fetch_remoteok_jobs()
    if not jobs:
        jobs = load_csv_fallback(csv_path)
    return jobs

def match_resume_to_jobs(resume_text, jobs_list, model):
    if not jobs_list:
        return []
    processed = preprocess_text(resume_text)
    resume_emb = model.encode([processed])
    descs = [preprocess_text(job.get('description', '')) for job in jobs_list]
    job_embs = model.encode(descs)
    scores = compute_similarity(resume_emb, job_embs)
    for job, score in zip(jobs_list, scores):
        job['similarity'] = float(score)
    return sorted(jobs_list, key=lambda x: x['similarity'], reverse=True)

# ---------- SCHOLARSHIP FUNCTIONS ----------
def fetch_scholarships(csv_path='scholarships.csv'):
    try:
        df = pd.read_csv(csv_path)
        return df.to_dict('records')
    except Exception as e:
        print(f"Error loading scholarships: {e}")
        return []

def analyze_scholarship_requirements(url):
    try:
        response = requests.get(url, timeout=15, headers={'User-Agent': 'Mozilla/5.0'})
        soup = BeautifulSoup(response.text, 'html.parser')
        text = soup.get_text()
        keywords = ['GPA', 'IELTS', 'TOEFL', 'recommendation', 'statement of purpose', 
                    'transcript', 'deadline', 'eligibility', 'requirement', 'documents',
                    'certificate', 'essay', 'CV', 'resume', 'application fee']
        found = []
        for kw in keywords:
            if kw.lower() in text.lower():
                sentences = re.split(r'[.!?]', text)
                for sent in sentences:
                    if kw.lower() in sent.lower() and len(sent.strip()) > 20:
                        found.append(f"• {sent.strip()}")
                        break
        if found:
            return "\n".join(found[:8])
        else:
            return "No specific requirements found. Please visit the official website."
    except Exception as e:
        return f"Could not fetch requirements: {str(e)}"

# ---------- CV DATA STORAGE ----------
CV_DATA_FILE = "cv_data.json"

def save_cv_data(email, cv_data):
    all_cv = {}
    if os.path.exists(CV_DATA_FILE):
        with open(CV_DATA_FILE, 'r', encoding='utf-8') as f:
            all_cv = json.load(f)
    all_cv[email] = cv_data
    with open(CV_DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(all_cv, f, indent=2)

def get_cv_data(email):
    if os.path.exists(CV_DATA_FILE):
        with open(CV_DATA_FILE, 'r', encoding='utf-8') as f:
            all_cv = json.load(f)
            return all_cv.get(email, None)
    return None

# ---------- PAYMENT STATUS ----------
PAYMENT_FILE = "payments.json"

def save_payment_status(email, feature, action, value=None):
    payments = {}
    if os.path.exists(PAYMENT_FILE):
        with open(PAYMENT_FILE, 'r', encoding='utf-8') as f:
            payments = json.load(f)
    if action == "set":
        if email not in payments:
            payments[email] = {}
        payments[email][feature] = value
        with open(PAYMENT_FILE, 'w', encoding='utf-8') as f:
            json.dump(payments, f, indent=2)
        return value
    else:
        return payments.get(email, {}).get(feature, False)

# ---------- PAYMENT VERIFICATION (simulated) ----------
def verify_flutterwave_payment(tx_ref):
    if tx_ref and len(tx_ref) > 5:
        return True
    return False