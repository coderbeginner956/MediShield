
# MediShield AI: Pharmaceutical Inspection, Counterfeit Risk Screening & Intelligence Platform

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-green.svg)](https://fastapi.tiangolo.com/)
[![Pytest](https://img.shields.io/badge/Tests-18%20Passed-brightgreen.svg)]()
[![Hardware](https://img.shields.io/badge/Hardware-100%25%20CPU%20(0%25%20GPU)-teal.svg)]()

> **Academic Project Submission**: Built as a presentation-ready pharmaceutical packaging visual inspection and risk-monitoring platform. Designed to run locally on standard laptop CPUs in **under 100 milliseconds** per image without requiring any dedicated GPU hardware.

---

## 1. Project Overview & Problem Statement

Counterfeit pharmaceuticals represent a grave global health hazard, causing hundreds of thousands of preventable deaths annually. Counterfeit packaging typically exhibits subtle defects:
- Missing, flat, or simulated holographic tamper-evident seals.
- Typographical anomalies, incorrect kerning, or subtle misspellings in brand/manufacturer names.
- Low-resolution printing or ink bleeding from consumer-grade digital printers.
- Expired shelf-life dates, invalid date formats, or non-existent batch numbers.
- Products matching active regulatory recalls.

**MediShield AI** does not rely on a naive binary black-box classifier. Instead, it combines **four independent pillars of evidence**:
1. **AI Visual Screening**: Surface gradient energy and bounding box localization.
2. **Approved Reference Comparison**: Pairwise ORB keypoint matching and difference overlays.
3. **OCR Label Inspection**: Text extraction, past-expiry detection, and typographical check.
4. **Regulatory Ledger Cross-Referencing**: Batch validation, manufacturer matching, and active recall alerts.

---

## 2. Technology Stack

* **Backend**: Python 3.11+, FastAPI, SQLAlchemy, SQLite, Pydantic, Pillow, OpenCV (Headless), Scikit-learn, ReportLab (PDF), PyJWT, Bcrypt, Pytest.
* **Frontend**: HTML5, Tailwind CSS, ES6 JavaScript, React / TypeScript architecture, Recharts, SVG Gauges, Canvas Overlays.
* **Hardware Profile**: **100% CPU Execution** (No CUDA / GPU memory required, runs at <150 MB RAM).

---

## 3. Key Features

1. **AI Medicine Image Screening**: Multi-factor feature evaluation supporting interchangeable providers (`demo`, `pretrained_cpu`, `unavailable`).
2. **Visual Explainability (XAI)**: Generates gradient saliency overlays and packaging landmark bounding boxes with honest limitation notices.
3. **Genuine Reference Comparison**: Side-by-side composite viewer showing Reference vs. Uploaded Specimen vs. Pixel Difference Heatmap.
4. **OCR Label Reader with Live Field Corrections**: Extracts brand name, manufacturer, lot code, and expiry date. Allows inspectors to correct fields and auto-recalibrates risk.
5. **Product & Batch Registry**: Relational database tracking formulations, shelf-life dates, and active recall notices.
6. **Case Management & PDF Reporting**: Escalation workflow for suspicious specimens, audit logging, and downloadable official PDF screening reports.

---

## 4. Quick Start Instructions

### Step 1: Start the Application Server
Open a terminal in `d:\Git\TE_project`:
```powershell
& "d:\Git\Solar_Project\.venv\Scripts\python.exe" -m uvicorn app.main:app --app-dir "d:\Git\TE_project\backend" --host 127.0.0.1 --port 8000
```
*(Or if you have python on your PATH: `cd backend && python -m uvicorn app.main:app --port 8000`)*

### Step 2: Open in Browser
* **Web Application**: [http://127.0.0.1:8000/](http://127.0.0.1:8000/)
* **Interactive API Docs (Swagger UI)**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

---

## 5. Public Sharing & Remote Deployment

MediShield AI includes built-in 1-click tools to share the live application over the internet with zero setup or paid accounts.

### Instant Public Share (Cloudflare Tunnel)
To generate a secure public HTTPS link that anyone worldwide can open on their phone or computer:
1. Double click `share_online.bat` in the project root (or run `.\cloudflared.exe tunnel --url http://127.0.0.1:8000`).
2. Copy the generated `.trycloudflare.com` URL displayed in the console.
3. Anyone with that link can immediately access the full live application, test live specimen uploads, and download PDF audit reports.

---

## 6. Pre-seeded Demo Accounts

| Role | Name | Email | Password |
| :--- | :--- | :--- | :--- |
| **Administrator** | Anushri | `admin@medishield.ai` | `admin123` |
| **Field Inspector** | Juee | `inspector@medishield.ai` | `inspector123` |
| **QA Reviewer** | Priti | `reviewer@medishield.ai` | `reviewer123` |

*(Note: You can switch active roles with 1 click directly in the web UI header!)*

---

## 7. Automated Testing

Run the test suite:
```powershell
cd d:\Git\TE_project\backend
& "d:\Git\Solar_Project\.venv\Scripts\python.exe" -m pytest tests/
```
**Results: 18 passed, 0 failed.**

---

## 8. Ethical Considerations & Statutory Disclaimer
MediShield AI is a software risk screening, optical triage, and investigative aid. It is **NOT** a certified medical device, chemical laboratory assay, or definitive guarantee of drug safety. Positive screening flags warrant immediate laboratory escalation to authorized health authorities.

