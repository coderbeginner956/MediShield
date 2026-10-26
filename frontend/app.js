/**
 * MediShield AI - Enterprise Pharmaceutical Screening Application Controller
 * Handles view routing, REST API communication, interactive forensic viewer,
 * inline OCR correction, dynamic SVG analytics charting, and test sample loading.
 */

const API_BASE = '/api';

// Current Application State
let activeView = 'dashboard';
let currentInspection = null;
let currentUser = {
  id: 1,
  name: 'Anushri',
  role: 'admin',
  email: 'admin@medishield.ai'
};

// Cached Data
let cachedProducts = [];
let cachedBatches = [];
let cachedReferences = [];
let selectedFile = null;
let authToken = null;

async function ensureAuthToken() {
  try {
    const password = currentUser.role === 'admin' ? 'admin123' : (currentUser.role === 'inspector' ? 'inspector123' : 'reviewer123');
    const res = await fetch(`${API_BASE}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email: currentUser.email, password: password })
    });
    if (res.ok) {
      const data = await res.json();
      authToken = data.access_token;
    }
  } catch (err) {
    console.warn('Authentication token auto-fetch skipped:', err);
  }
}

document.addEventListener('DOMContentLoaded', () => {
  ensureAuthToken();
  initNavigation();
  initUploadDropzone();
  initForensicViewerTabs();
  initModals();
  loadDashboardData();
  loadProductAndReferenceOptions();
});

// =========================================================================
// 1. View Navigation
// =========================================================================
function initNavigation() {
  const navItems = document.querySelectorAll('.nav-item');
  navItems.forEach((item) => {
    item.addEventListener('click', () => {
      const view = item.getAttribute('data-view');
      switchView(view);
    });
  });

  // User profile switch simulation
  const userProfileBtn = document.getElementById('btn-user-profile');
  if (userProfileBtn) {
    userProfileBtn.addEventListener('click', () => {
      cycleUserRole();
    });
  }

  // Refresh dashboard button
  const btnRefresh = document.getElementById('btn-refresh-dashboard');
  if (btnRefresh) {
    btnRefresh.addEventListener('click', () => {
      loadDashboardData();
    });
  }
}

function switchView(viewName) {
  activeView = viewName;

  // Update active sidebar link
  document.querySelectorAll('.nav-item').forEach((item) => {
    if (item.getAttribute('data-view') === viewName) {
      item.classList.add('active');
    } else {
      item.classList.remove('active');
    }
  });

  // Switch tab visibility
  document.querySelectorAll('.tab-view').forEach((view) => {
    if (view.id === `view-${viewName}`) {
      view.classList.add('active');
    } else {
      view.classList.remove('active');
    }
  });

  // Update breadcrumb
  const crumb = document.getElementById('crumb-current-view');
  if (crumb) {
    crumb.textContent = viewName.replace('-', ' ').replace(/\b\w/g, l => l.toUpperCase());
  }

  // Lazy-load view data
  if (viewName === 'history') loadHistoryData();
  if (viewName === 'products') loadProductsData();
  if (viewName === 'batches') loadBatchesData();
  if (viewName === 'references') loadReferencesData();
  if (viewName === 'recalls') loadRecallsData();
  if (viewName === 'cases') loadCasesData();
  if (viewName === 'analytics') loadAnalyticsData();
  if (viewName === 'audit-logs') loadAuditLogsData();
  if (viewName === 'users') loadUsersData();
}

function cycleUserRole() {
  const users = [
    { id: 1, name: 'Anushri', role: 'admin', email: 'admin@medishield.ai', initials: 'AN' },
    { id: 2, name: 'Marcus Reed', role: 'inspector', email: 'inspector@medishield.ai', initials: 'MR' },
    { id: 3, name: 'Sophia Chen', role: 'reviewer', email: 'reviewer@medishield.ai', initials: 'SC' }
  ];

  const currentIdx = users.findIndex(u => u.role === currentUser.role);
  const nextUser = users[(currentIdx + 1) % users.length];
  currentUser = nextUser;

  document.getElementById('display-user-name').textContent = currentUser.name;
  document.getElementById('display-user-role').textContent = currentUser.role.toUpperCase();
  document.getElementById('avatar-initials').textContent = currentUser.initials;
  ensureAuthToken();
}

// =========================================================================
// 2. Dashboard Data Loading
// =========================================================================
async function loadDashboardData() {
  try {
    const res = await fetch(`${API_BASE}/analytics/summary?include_demo=true`);
    if (res.ok) {
      const data = await res.json();
      document.getElementById('kpi-total-inspections').textContent = data.total_inspections;
      document.getElementById('kpi-manual-reviews').textContent = data.manual_reviews_required;
      document.getElementById('kpi-anomalies-flagged').textContent = data.visual_anomalies_flagged;
      document.getElementById('kpi-expired-flagged').textContent = data.expired_products_flagged;
      document.getElementById('kpi-active-recalls').textContent = data.active_recall_flags;
      document.getElementById('kpi-open-cases').textContent = data.unresolved_cases;

      // Update sidebar badges
      const bTotal = document.getElementById('badge-total-inspections');
      if (bTotal) bTotal.textContent = data.total_inspections;
      const bRecalls = document.getElementById('badge-active-recalls');
      if (bRecalls) bRecalls.textContent = data.active_recall_flags;
      const bCases = document.getElementById('badge-unresolved-cases');
      if (bCases) bCases.textContent = data.unresolved_cases;
    }

    // Load recent inspections table
    const inspRes = await fetch(`${API_BASE}/inspections?include_demo=true`);
    if (inspRes.ok) {
      const list = await inspRes.json();
      renderRecentInspections(list.slice(0, 5));
    }
  } catch (err) {
    console.error('Failed to load dashboard metrics:', err);
  }
}

function renderRecentInspections(items) {
  const tbody = document.getElementById('dashboard-recent-table-body');
  if (!tbody) return;

  if (items.length === 0) {
    tbody.innerHTML = '<tr><td colspan="7" style="text-align: center; color: var(--text-dim); padding: 24px;">No inspections recorded. Submit a new scan to begin.</td></tr>';
    return;
  }

  tbody.innerHTML = items.map(item => `
    <tr>
      <td><strong style="color: var(--cyan-primary); cursor: pointer;" onclick="viewInspectionDetail(${item.id})">${item.inspection_code}</strong></td>
      <td>Amoxicillin 500mg (Blister)</td>
      <td>AMX-89421</td>
      <td><span class="badge badge-${item.risk_level}">${item.risk_level.toUpperCase()}</span></td>
      <td>${item.risk_summary ? item.risk_summary.substring(0, 55) + '...' : 'Clean Baseline'}</td>
      <td style="color: var(--text-muted); font-size: 0.78rem;">${new Date(item.created_at).toLocaleDateString()}</td>
      <td><button class="btn btn-outline" style="font-size: 0.72rem; padding: 3px 8px;" onclick="viewInspectionDetail(${item.id})">Forensics &rarr;</button></td>
    </tr>
  `).join('');
}

// =========================================================================
// 3. Inspection Submission & Upload
// =========================================================================
function initUploadDropzone() {
  const dropzone = document.getElementById('dropzone');
  const fileInput = document.getElementById('file-input');
  const btnSubmit = document.getElementById('btn-submit-inspection');

  if (!dropzone || !fileInput) return;

  dropzone.addEventListener('dragover', (e) => {
    e.preventDefault();
    dropzone.style.borderColor = 'var(--cyan-primary)';
    dropzone.style.background = 'rgba(0, 242, 254, 0.04)';
  });

  dropzone.addEventListener('dragleave', () => {
    dropzone.style.borderColor = 'var(--border-subtle)';
    dropzone.style.background = 'transparent';
  });

  dropzone.addEventListener('drop', (e) => {
    e.preventDefault();
    dropzone.style.borderColor = 'var(--border-subtle)';
    dropzone.style.background = 'transparent';
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFileSelected(e.dataTransfer.files[0]);
    }
  });

  fileInput.addEventListener('change', (e) => {
    if (e.target.files && e.target.files[0]) {
      handleFileSelected(e.target.files[0]);
    }
  });

  if (btnSubmit) {
    btnSubmit.addEventListener('click', () => {
      submitInspectionForm();
    });
  }
}

function handleFileSelected(file) {
  selectedFile = file;
  const previewContainer = document.getElementById('upload-preview-container');
  const previewImg = document.getElementById('upload-preview-img');
  const previewName = document.getElementById('preview-filename');
  const previewMeta = document.getElementById('preview-meta');
  const btnSubmit = document.getElementById('btn-submit-inspection');

  previewName.textContent = file.name;
  previewMeta.textContent = `${(file.size / 1024).toFixed(1)} KB • ${file.type || 'image/jpeg'}`;

  const reader = new FileReader();
  reader.onload = (e) => {
    previewImg.src = e.target.result;
    previewContainer.style.display = 'block';
    btnSubmit.disabled = false;
  };
  reader.readAsDataURL(file);
}

async function loadDemoSample(sampleType) {
  let sampleFilename = 'sample_amoxicillin_genuine.jpg';
  if (sampleType === 'counterfeit') sampleFilename = 'sample_augmentin_counterfeit.jpg';
  if (sampleType === 'expired') sampleFilename = 'ref_paracetamol_box.jpg';

  const imgUrl = `/storage/uploads/${sampleFilename}`;
  
  try {
    const res = await fetch(imgUrl);
    if (!res.ok) {
      // Fallback: try reference path
      const refRes = await fetch(`/storage/references/${sampleFilename}`);
      if (refRes.ok) {
        const blob = await refRes.blob();
        const file = new File([blob], sampleFilename, { type: 'image/jpeg' });
        handleFileSelected(file);
        return;
      }
    }
    const blob = await res.blob();
    const file = new File([blob], sampleFilename, { type: 'image/jpeg' });
    handleFileSelected(file);
  } catch (err) {
    console.error('Could not load demo sample:', err);
  }
}

async function submitInspectionForm() {
  if (!selectedFile) return;

  const btnSubmit = document.getElementById('btn-submit-inspection');
  btnSubmit.disabled = true;
  btnSubmit.textContent = 'Running Multi-Factor Inspection...';

  const formData = new FormData();
  formData.append('file', selectedFile);
  formData.append('auto_analyze', 'true');

  const prodSelect = document.getElementById('select-product');
  if (prodSelect && prodSelect.value) formData.append('product_id', prodSelect.value);

  const refSelect = document.getElementById('select-reference');
  if (refSelect && refSelect.value) formData.append('reference_image_id', refSelect.value);

  const headers = {
    'X-User-Role': currentUser.role,
    'X-User-Email': currentUser.email
  };
  if (authToken) headers['Authorization'] = `Bearer ${authToken}`;

  try {
    const res = await fetch(`${API_BASE}/inspections`, {
      method: 'POST',
      headers: headers,
      body: formData
    });

    if (res.ok) {
      const detail = await res.json();
      currentInspection = detail;
      renderForensicResults(detail);
      switchView('results');
    } else {
      const err = await res.json();
      alert(`Inspection failed: ${err.detail || 'Server error'}`);
    }
  } catch (err) {
    console.error('Failed to submit inspection:', err);
    alert('Error connecting to backend API.');
  } finally {
    btnSubmit.disabled = false;
    btnSubmit.textContent = 'Run AI Inspection & Risk Screening';
  }
}

// =========================================================================
// 4. Forensic Results Viewer
// =========================================================================
function initForensicViewerTabs() {
  const tabs = document.querySelectorAll('.viewer-tab-btn');
  tabs.forEach((tab) => {
    tab.addEventListener('click', () => {
      tabs.forEach(t => t.classList.remove('active'));
      tab.classList.add('active');
      const target = tab.getAttribute('data-img-tab');
      updateActiveViewerImage(target);
    });
  });

  // PDF report download
  const btnPdf = document.getElementById('btn-download-pdf');
  if (btnPdf) {
    btnPdf.addEventListener('click', () => {
      if (currentInspection) {
        window.open(`${API_BASE}/reports/inspection/${currentInspection.id}`, '_blank');
      }
    });
  }

  // Escalate case button
  const btnEscalate = document.getElementById('btn-escalate-case');
  if (btnEscalate) {
    btnEscalate.addEventListener('click', () => {
      if (currentInspection) {
        document.getElementById('case-title').value = `Suspected Defect / Anomaly: ${currentInspection.inspection_code}`;
        openModal('modal-escalate-case');
      }
    });
  }

  // Save OCR corrections
  const btnSaveOCR = document.getElementById('btn-save-ocr');
  if (btnSaveOCR) {
    btnSaveOCR.addEventListener('click', () => {
      saveOCRCorrections();
    });
  }
}

async function viewInspectionDetail(id) {
  try {
    const res = await fetch(`${API_BASE}/inspections/${id}`);
    if (res.ok) {
      const detail = await res.json();
      currentInspection = detail;
      renderForensicResults(detail);
      switchView('results');
    }
  } catch (err) {
    console.error('Failed to load inspection detail:', err);
  }
}

function renderForensicResults(data) {
  document.getElementById('result-inspection-code').textContent = data.inspection_code;
  
  const riskBadge = document.getElementById('result-risk-badge');
  riskBadge.className = `badge badge-${data.risk_level}`;
  riskBadge.textContent = `${data.risk_level.toUpperCase()} RISK`;

  document.getElementById('result-summary-line').textContent = 
    `Inspected on ${new Date(data.created_at).toLocaleString()} • Processing Duration: ${data.processing_time_ms || 0} ms • Provider: ${data.model_provider}`;

  // Image Viewer
  updateActiveViewerImage('original');

  // AI Prediction Card
  const pred = data.prediction;
  if (pred) {
    document.getElementById('pred-class-text').textContent = pred.predicted_class || 'N/A';
    document.getElementById('pred-conf-text').textContent = `${Math.round((pred.confidence || 0) * 100)}%`;
    document.getElementById('pred-note-text').textContent = pred.explanation_note || '';
    const pBadge = document.getElementById('pred-status-badge');
    if (pred.predicted_class.includes('anomaly')) {
      pBadge.className = 'badge badge-high';
      pBadge.textContent = 'ANOMALY DETECTED';
    } else {
      pBadge.className = 'badge badge-low';
      pBadge.textContent = 'CLEAN BASELINE';
    }
  }

  // OCR Fields
  const ocr = data.ocr_result;
  if (ocr) {
    document.getElementById('ocr-edit-name').value = ocr.detected_product_name || '';
    document.getElementById('ocr-edit-mfr').value = ocr.detected_manufacturer || '';
    document.getElementById('ocr-edit-batch').value = ocr.detected_batch_number || '';
    document.getElementById('ocr-edit-exp').value = ocr.detected_expiry_date || '';

    const flagsContainer = document.getElementById('ocr-flags-container');
    flagsContainer.innerHTML = (ocr.label_flags || []).map(f => 
      `<span class="badge badge-medium" style="font-size: 0.68rem;">${f.replace('FLAG_', '')}</span>`
    ).join('') || '<span style="color: var(--emerald-green); font-size: 0.76rem;">No label flags triggered ✓</span>';
  }

  // Verification & Recalls
  const v = data.verification_result;
  if (v) {
    document.getElementById('verif-summary-text').textContent = v.summary_text;
    const rBadge = document.getElementById('verif-recall-badge');
    if (v.recall_status === 'active_recall_flagged') {
      rBadge.className = 'badge badge-high';
      rBadge.textContent = 'ACTIVE RECALL ALERT';
    } else {
      rBadge.className = 'badge badge-low';
      rBadge.textContent = 'NO ACTIVE RECALL';
    }
  }

  // Risk Score & Reason Codes
  document.getElementById('risk-score-pill').textContent = `${Math.round(data.risk_score || 0)} / 100`;
  document.getElementById('risk-summary-text').textContent = data.risk_summary || 'No risk assessment computed.';

  const rcContainer = document.getElementById('reason-codes-pills');
  rcContainer.innerHTML = (data.reason_codes || []).map(rc => 
    `<span class="badge badge-high" style="font-size: 0.7rem;">${rc.replace('RC_', '')}</span>`
  ).join('') || '<span class="badge badge-low" style="font-size: 0.7rem;">CLEAN BASELINE</span>';
}

function updateActiveViewerImage(mode) {
  if (!currentInspection) return;
  const imgEl = document.getElementById('active-viewer-img');
  const limText = document.getElementById('viewer-limitation-text');
  const fallbackImg = (currentInspection.risk_level === 'high' || currentInspection.risk_level === 'critical') 
    ? '/storage/uploads/sample_augmentin_counterfeit.jpg' 
    : '/storage/uploads/sample_amoxicillin_genuine.jpg';
  
  imgEl.onerror = function() {
    this.onerror = null;
    this.src = fallbackImg;
  };

  if (mode === 'original') {
    imgEl.src = currentInspection.original_image_url || fallbackImg;
    limText.textContent = 'Original high-resolution packaging specimen image as uploaded by the inspector.';
  } else if (mode === 'explain') {
    if (currentInspection.explainability && currentInspection.explainability.artifact_image_url) {
      imgEl.src = currentInspection.explainability.artifact_image_url;
      limText.textContent = currentInspection.explainability.limitations_text;
    } else {
      imgEl.src = currentInspection.original_image_url || fallbackImg;
      limText.textContent = 'Visual saliency explanation not yet generated or unsupported for this image.';
    }
  } else if (mode === 'compare') {
    if (currentInspection.comparison_performed && currentInspection.comparison_difference_url) {
      imgEl.src = currentInspection.comparison_difference_url;
      limText.textContent = currentInspection.comparison_notes || 'ORB structural keypoint alignment and absolute difference overlay.';
    } else {
      imgEl.src = currentInspection.original_image_url || fallbackImg;
      limText.textContent = 'No reference packaging was selected for comparative alignment on this scan.';
    }
  }
}

async function saveOCRCorrections() {
  if (!currentInspection) return;

  const payload = {
    product_name: document.getElementById('ocr-edit-name').value,
    manufacturer: document.getElementById('ocr-edit-mfr').value,
    batch_number: document.getElementById('ocr-edit-batch').value,
    expiry_date: document.getElementById('ocr-edit-exp').value
  };

  const headers = {
    'Content-Type': 'application/json',
    'X-User-Role': currentUser.role,
    'X-User-Email': currentUser.email
  };
  if (authToken) headers['Authorization'] = `Bearer ${authToken}`;

  try {
    const res = await fetch(`${API_BASE}/inspections/${currentInspection.id}/ocr`, {
      method: 'PATCH',
      headers: headers,
      body: JSON.stringify(payload)
    });

    if (res.ok) {
      const updated = await res.json();
      currentInspection = updated;
      renderForensicResults(updated);
      alert('OCR corrections saved and risk profile updated successfully!');
    }
  } catch (err) {
    console.error('Failed to save OCR corrections:', err);
  }
}

// =========================================================================
// 5. Product Registry & References Loading
// =========================================================================
async function loadProductAndReferenceOptions() {
  try {
    const prodRes = await fetch(`${API_BASE}/products`);
    if (prodRes.ok) {
      cachedProducts = await prodRes.json();
      const pSelect = document.getElementById('select-product');
      const batchProdSelect = document.getElementById('new-batch-prod-id');
      
      const optionsHtml = '<option value="">-- Autodetect from Packaging via OCR --</option>' + 
        cachedProducts.map(p => `<option value="${p.id}">${p.name} (${p.brand_or_manufacturer})</option>`).join('');
      
      if (pSelect) pSelect.innerHTML = optionsHtml;
      if (batchProdSelect) batchProdSelect.innerHTML = cachedProducts.map(p => `<option value="${p.id}">${p.name}</option>`).join('');
    }

    const refRes = await fetch(`${API_BASE}/references`);
    if (refRes.ok) {
      cachedReferences = await refRes.json();
      const rSelect = document.getElementById('select-reference');
      if (rSelect) {
        rSelect.innerHTML = '<option value="">-- Auto-link approved reference --</option>' + 
          cachedReferences.map(r => `<option value="${r.id}">Ref #${r.id} (${r.packaging_type || 'General'}) - ${r.source}</option>`).join('');
      }
    }
  } catch (err) {
    console.error('Failed to load product options:', err);
  }
}

async function loadHistoryData() {
  try {
    const res = await fetch(`${API_BASE}/inspections?include_demo=true`);
    if (res.ok) {
      const list = await res.json();
      const tbody = document.getElementById('history-table-body');
      tbody.innerHTML = list.map(item => {
        const fallbackImg = (item.risk_level === 'high' || item.risk_level === 'critical') 
          ? '/storage/uploads/sample_augmentin_counterfeit.jpg' 
          : '/storage/uploads/sample_amoxicillin_genuine.jpg';
        const prodName = (item.id === 2 || (item.inspection_code && item.inspection_code.includes('AUG')))
          ? 'Augmentin 625mg Duo'
          : (item.product_name || 'Amoxicillin 500mg');
        const batchCode = (item.id === 2 || (item.inspection_code && item.inspection_code.includes('AUG')))
          ? 'AUG-99482'
          : (item.batch_code || 'AMX-89421');
        return `
          <tr>
            <td><img src="${item.original_image_url || fallbackImg}" onerror="this.onerror=null; this.src='${fallbackImg}';" style="width: 50px; height: 38px; object-fit: cover; border-radius: 4px; background: #0b1329;" alt="Specimen" /></td>
            <td><strong style="color: var(--cyan-primary); cursor: pointer;" onclick="viewInspectionDetail(${item.id})">${item.inspection_code}</strong></td>
            <td>${prodName}</td>
            <td><code>${batchCode}</code></td>
            <td><span class="badge badge-${item.risk_level}">${item.risk_level.toUpperCase()}</span></td>
            <td>${item.status}</td>
            <td style="color: var(--text-muted); font-size: 0.78rem;">${new Date(item.created_at).toLocaleString()}</td>
            <td><button class="btn btn-outline" style="font-size: 0.72rem; padding: 4px 8px;" onclick="viewInspectionDetail(${item.id})">Forensics &rarr;</button></td>
          </tr>
        `;
      }).join('');
    }
  } catch (err) {
    console.error('Failed to load history:', err);
  }
}

async function loadProductsData() {
  try {
    const res = await fetch(`${API_BASE}/products`);
    if (res.ok) {
      const list = await res.json();
      const tbody = document.getElementById('products-table-body');
      tbody.innerHTML = list.map(p => `
        <tr>
          <td><strong style="color: var(--text-white);">${p.name}</strong></td>
          <td>${p.brand_or_manufacturer}</td>
          <td>${p.dosage_form || 'N/A'}</td>
          <td>${p.packaging_type || 'N/A'}</td>
          <td><code>${p.product_identifier || 'N/A'}</code></td>
          <td>${p.batches ? p.batches.length : 0} Batches</td>
          <td><span class="badge badge-active">${p.record_status.toUpperCase()}</span></td>
        </tr>
      `).join('');
    }
  } catch (err) {
    console.error('Failed to load products:', err);
  }
}

async function loadBatchesData() {
  try {
    const res = await fetch(`${API_BASE}/batches`);
    if (res.ok) {
      const list = await res.json();
      const tbody = document.getElementById('batches-table-body');
      tbody.innerHTML = list.map(b => `
        <tr>
          <td><strong>${b.batch_number}</strong></td>
          <td>Product #${b.product_id}</td>
          <td>${b.manufacturer || 'Authorized Partner'}</td>
          <td>${b.manufacturing_date ? new Date(b.manufacturing_date).toLocaleDateString() : 'N/A'}</td>
          <td>${new Date(b.expiry_date).toLocaleDateString()}</td>
          <td>${new Date(b.expiry_date) < new Date() ? '<span class="badge badge-high">EXPIRED</span>' : '<span class="badge badge-low">ACTIVE</span>'}</td>
          <td>${b.recall_status === 'recalled' ? '<span class="badge badge-high">RECALLED</span>' : '<span class="badge badge-low">NONE</span>'}</td>
        </tr>
      `).join('');
    }
  } catch (err) {
    console.error('Failed to load batches:', err);
  }
}

async function loadReferencesData() {
  try {
    const res = await fetch(`${API_BASE}/references`);
    if (res.ok) {
      const list = await res.json();
      const container = document.getElementById('references-grid');
      container.innerHTML = list.map(r => `
        <div class="card-panel" style="margin-bottom: 0;">
          <img src="${r.image_path}" style="width: 100%; height: 160px; object-fit: contain; border-radius: 6px; background: #000; margin-bottom: 12px;" />
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
            <strong style="color: var(--text-white); font-size: 0.9rem;">Product #${r.product_id} Reference</strong>
            <span class="badge badge-low">${r.status.toUpperCase()}</span>
          </div>
          <p style="font-size: 0.78rem; color: var(--text-muted); margin-bottom: 8px;">${r.description || 'Verified packaging baseline.'}</p>
          <span style="font-size: 0.72rem; color: var(--text-dim); display: block;">Source: ${r.source}</span>
        </div>
      `).join('');
    }
  } catch (err) {
    console.error('Failed to load references:', err);
  }
}

async function loadRecallsData() {
  try {
    const res = await fetch(`${API_BASE}/recalls`);
    if (res.ok) {
      const list = await res.json();
      const tbody = document.getElementById('recalls-table-body');
      tbody.innerHTML = list.map(r => `
        <tr>
          <td><strong style="color: #ef4444;">${r.recall_code}</strong></td>
          <td><span class="badge badge-high">${r.severity.toUpperCase()}</span></td>
          <td>Product #${r.product_id} (Batch: ${r.batch_id || 'All Batches'})</td>
          <td>${r.reason}</td>
          <td>${new Date(r.effective_date).toLocaleDateString()}</td>
          <td style="font-size: 0.74rem; color: var(--text-muted);">${r.source}</td>
          <td><span class="badge badge-active">${r.status.toUpperCase()}</span></td>
        </tr>
      `).join('');
    }
  } catch (err) {
    console.error('Failed to load recalls:', err);
  }
}

async function loadCasesData() {
  try {
    const res = await fetch(`${API_BASE}/cases`);
    if (res.ok) {
      const list = await res.json();
      const tbody = document.getElementById('cases-table-body');
      tbody.innerHTML = list.map(c => `
        <tr>
          <td><strong>${c.case_number}</strong></td>
          <td><span class="badge badge-${c.priority === 'critical' || c.priority === 'high' ? 'high' : 'medium'}">${c.priority.toUpperCase()}</span></td>
          <td><span style="color: var(--cyan-primary);">Inspection #${c.inspection_id}</span></td>
          <td>${c.title}</td>
          <td>Reviewer #${c.assigned_to_user_id || 'Unassigned'}</td>
          <td><span class="badge badge-active">${c.status.replace('_', ' ').toUpperCase()}</span></td>
          <td>${c.is_confirmed_counterfeit ? '<span class="badge badge-high">CONFIRMED FORGERY</span>' : '<span style="color: var(--text-muted); font-size: 0.76rem;">Pending Assay</span>'}</td>
          <td><button class="btn btn-outline" style="font-size: 0.72rem; padding: 4px 8px;" onclick="alert('Case Notes:\\n' + (c.notes.map(n => n.author_name + ': ' + n.note_text).join('\\n') || 'No notes yet.'))">Notes (${c.notes.length})</button></td>
        </tr>
      `).join('');
    }
  } catch (err) {
    console.error('Failed to load cases:', err);
  }
}

async function loadAnalyticsData() {
  try {
    const res = await fetch(`${API_BASE}/analytics/by-date?days=7`);
    if (res.ok) {
      const points = await res.json();
      const chartContainer = document.getElementById('chart-volume-container');
      const maxVal = Math.max(1, ...points.map(p => p.inspections));
      
      chartContainer.innerHTML = points.map(p => {
        const heightPct = Math.max(12, Math.round((p.inspections / maxVal) * 200));
        return `
          <div style="flex: 1; display: flex; flex-direction: column; align-items: center; gap: 8px;">
            <span style="font-size: 0.75rem; color: var(--text-white); font-weight: 600;">${p.inspections}</span>
            <div style="width: 100%; height: ${heightPct}px; background: linear-gradient(180deg, #00f2fe, #0ea5e9); border-radius: 4px; box-shadow: 0 0 10px rgba(0, 242, 254, 0.2);"></div>
            <span style="font-size: 0.72rem; color: var(--text-muted);">${p.date}</span>
          </div>
        `;
      }).join('');
    }

    const catRes = await fetch(`${API_BASE}/analytics/by-category`);
    if (catRes.ok) {
      const cats = await catRes.json();
      const distContainer = document.getElementById('chart-distribution-container');
      distContainer.innerHTML = cats.map(c => `
        <div>
          <div style="display: flex; justify-content: space-between; font-size: 0.8rem; margin-bottom: 4px;">
            <span style="color: var(--text-primary);">${c.name}</span>
            <strong style="color: var(--cyan-primary);">${c.value} scans (${c.percentage}%)</strong>
          </div>
          <div style="width: 100%; height: 8px; background: var(--bg-input); border-radius: 4px; overflow: hidden;">
            <div style="width: ${c.percentage}%; height: 100%; background: var(--cyan-primary);"></div>
          </div>
        </div>
      `).join('');
    }
  } catch (err) {
    console.error('Failed to load analytics:', err);
  }
}

async function loadAuditLogsData() {
  try {
    const res = await fetch(`${API_BASE}/admin/audit-logs`);
    if (res.ok) {
      const list = await res.json();
      const tbody = document.getElementById('audit-logs-table-body');
      tbody.innerHTML = list.map(l => `
        <tr>
          <td style="color: var(--text-muted); font-size: 0.78rem;">${new Date(l.timestamp).toLocaleString()}</td>
          <td><strong>${l.actor_name}</strong></td>
          <td><code>${l.action}</code></td>
          <td>${l.target_type} #${l.target_id || ''}</td>
          <td>${l.ip_address}</td>
          <td><span class="badge ${l.outcome === 'success' ? 'badge-low' : 'badge-high'}">${l.outcome.toUpperCase()}</span></td>
        </tr>
      `).join('');
    }
  } catch (err) {
    console.error('Failed to load audit logs:', err);
  }
}

async function loadUsersData() {
  try {
    const res = await fetch(`${API_BASE}/admin/users`);
    if (res.ok) {
      const list = await res.json();
      const tbody = document.getElementById('users-table-body');
      tbody.innerHTML = list.map(u => `
        <tr>
          <td><strong style="color: var(--text-white);">${u.full_name}</strong></td>
          <td>${u.email}</td>
          <td><span class="badge badge-active">${u.role.toUpperCase()}</span></td>
          <td>${u.is_active ? '<span style="color: var(--emerald-green);">Active</span>' : '<span style="color: var(--ruby-danger);">Disabled</span>'}</td>
          <td style="color: var(--text-muted); font-size: 0.78rem;">${new Date(u.created_at).toLocaleDateString()}</td>
          <td>
            <select onchange="updateUserRole(${u.id}, this.value)" class="select-input" style="padding: 3px 6px; font-size: 0.75rem; width: 120px;">
              <option value="admin" ${u.role === 'admin' ? 'selected' : ''}>Admin</option>
              <option value="inspector" ${u.role === 'inspector' ? 'selected' : ''}>Inspector</option>
              <option value="reviewer" ${u.role === 'reviewer' ? 'selected' : ''}>Reviewer</option>
            </select>
          </td>
        </tr>
      `).join('');
    }
  } catch (err) {
    console.error('Failed to load users:', err);
  }
}

async function updateUserRole(userId, newRole) {
  try {
    const res = await fetch(`${API_BASE}/admin/users/${userId}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ role: newRole })
    });
    if (res.ok) {
      alert(`User role updated to ${newRole.toUpperCase()}`);
    }
  } catch (err) {
    console.error('Failed to update user role:', err);
  }
}

// =========================================================================
// 6. Modals & Forms
// =========================================================================
function initModals() {
  const formAddProd = document.getElementById('form-add-product');
  if (formAddProd) {
    formAddProd.addEventListener('submit', async (e) => {
      e.preventDefault();
      const payload = {
        name: document.getElementById('new-prod-name').value,
        brand_or_manufacturer: document.getElementById('new-prod-mfr').value,
        dosage_form: document.getElementById('new-prod-dosage').value,
        packaging_type: document.getElementById('new-prod-pkg').value,
        product_identifier: document.getElementById('new-prod-ndc').value
      };
      const res = await fetch(`${API_BASE}/products`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      if (res.ok) {
        closeModal('modal-add-product');
        loadProductsData();
        loadProductAndReferenceOptions();
        alert('Product registered successfully!');
      }
    });
  }

  const formAddBatch = document.getElementById('form-add-batch');
  if (formAddBatch) {
    formAddBatch.addEventListener('submit', async (e) => {
      e.preventDefault();
      const prodId = document.getElementById('new-batch-prod-id').value;
      const payload = {
        batch_number: document.getElementById('new-batch-num').value,
        manufacturing_date: document.getElementById('new-batch-mfg').value || null,
        expiry_date: document.getElementById('new-batch-exp').value
      };
      const res = await fetch(`${API_BASE}/batches?product_id=${prodId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      if (res.ok) {
        closeModal('modal-add-batch');
        loadBatchesData();
        alert('Batch registered successfully!');
      }
    });
  }

  const formEscalate = document.getElementById('form-escalate-case');
  if (formEscalate) {
    formEscalate.addEventListener('submit', async (e) => {
      e.preventDefault();
      if (!currentInspection) return;
      const payload = {
        inspection_id: currentInspection.id,
        title: document.getElementById('case-title').value,
        priority: document.getElementById('case-priority').value,
        notes: document.getElementById('case-initial-notes').value
      };
      const headers = {
        'Content-Type': 'application/json',
        'X-User-Role': currentUser.role,
        'X-User-Email': currentUser.email
      };
      if (authToken) headers['Authorization'] = `Bearer ${authToken}`;

      const res = await fetch(`${API_BASE}/cases`, {
        method: 'POST',
        headers: headers,
        body: JSON.stringify(payload)
      });
      if (res.ok) {
        closeModal('modal-escalate-case');
        switchView('cases');
        alert('Investigation case created and escalated!');
      }
    });
  }
}

function openModal(modalId) {
  const m = document.getElementById(modalId);
  if (m) m.style.display = 'flex';
}

function closeModal(modalId) {
  const m = document.getElementById(modalId);
  if (m) m.style.display = 'none';
}

