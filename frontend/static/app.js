// ============================================================================
// OCR Prescription Intelligence - Complete JavaScript Application
// ============================================================================

// Global Variables
let currentResults = null;
let startTime = Date.now();

// ============================================================================
// INITIALIZATION
// ============================================================================

document.addEventListener('DOMContentLoaded', function () {
    console.log('OCR Prescription Intelligence initialized');

    // Initialize all components
    initializeNavigation();
    initializeUpload();
    initializeForms();
    initializeDashboard();

    // Start uptime tracking
    setInterval(updateUptime, 1000);

    // Handle initial hash navigation
    if (window.location.hash) {
        const section = window.location.hash.substring(1);
        navigateToSection(section);
    }
});

// ============================================================================
// NAVIGATION
// ============================================================================

function initializeNavigation() {
    // Handle nav link clicks
    document.querySelectorAll('.nav-link').forEach(link => {
        link.addEventListener('click', function (e) {
            e.preventDefault();
            const section = this.dataset.section || this.getAttribute('href').substring(1);
            navigateToSection(section);
        });
    });

    // Handle browser back/forward
    window.addEventListener('hashchange', function () {
        if (window.location.hash) {
            const section = window.location.hash.substring(1);
            navigateToSection(section, false);
        }
    });
}

function navigateToSection(sectionId, updateHash = true) {
    // Hide all sections
    document.querySelectorAll('.page-section').forEach(section => {
        section.classList.remove('active');
    });

    // Show target section
    const targetSection = document.getElementById(sectionId);
    if (targetSection) {
        targetSection.classList.add('active');
    }

    // Update nav active state
    document.querySelectorAll('.nav-link').forEach(link => {
        link.classList.remove('active');
        if (link.dataset.section === sectionId || link.getAttribute('href') === '#' + sectionId) {
            link.classList.add('active');
        }
    });

    // Update URL hash
    if (updateHash) {
        window.location.hash = sectionId;
    }

    // Scroll to top
    window.scrollTo({ top: 0, behavior: 'smooth' });

    // Initialize section-specific functionality
    if (sectionId === 'dashboard') {
        checkSystemHealth();
        loadStats();
    }
}

// ============================================================================
// FILE UPLOAD
// ============================================================================

function initializeUpload() {
    const dropZone = document.getElementById('dropZone');
    const imageFile = document.getElementById('imageFile');

    if (!dropZone || !imageFile) return;

    // Click to upload
    dropZone.addEventListener('click', () => imageFile.click());

    // Drag and drop handlers
    dropZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropZone.classList.add('drag-over');
    });

    dropZone.addEventListener('dragleave', () => {
        dropZone.classList.remove('drag-over');
    });

    dropZone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropZone.classList.remove('drag-over');

        if (e.dataTransfer.files.length) {
            imageFile.files = e.dataTransfer.files;
            updateDropZoneText(e.dataTransfer.files[0].name);
        }
    });

    // File input change
    imageFile.addEventListener('change', () => {
        if (imageFile.files.length) {
            updateDropZoneText(imageFile.files[0].name);
        }
    });
}

function updateDropZoneText(filename) {
    const dropZone = document.getElementById('dropZone');
    if (dropZone) {
        const textElement = dropZone.querySelector('p');
        if (textElement) {
            textElement.textContent = filename;
        }
    }
}

// ============================================================================
// FORM HANDLING
// ============================================================================

function initializeForms() {
    // Image form submission
    const imageForm = document.getElementById('imageForm');
    if (imageForm) {
        imageForm.addEventListener('submit', handleImageSubmit);
    }

    // Text form submission
    const textForm = document.getElementById('textForm');
    if (textForm) {
        textForm.addEventListener('submit', handleTextSubmit);
    }

    // Contact form submission
    const contactForm = document.getElementById('contactForm');
    if (contactForm) {
        contactForm.addEventListener('submit', handleContactSubmit);
    }
}

async function handleImageSubmit(e) {
    e.preventDefault();

    const imageFile = document.getElementById('imageFile');

    if (!imageFile.files.length) {
        showNotification('Please select a file', 'error');
        return;
    }

    // Show loading state
    showLoading('Processing image...');

    const formData = new FormData();
    formData.append('file', imageFile.files[0]);

    try {
        const response = await fetch('/api/process-image', {
            method: 'POST',
            body: formData
        });

        const data = await response.json();

        hideLoading();

        if (data.success) {
            displayResults(data.data);
            showNotification('Analysis complete!', 'success');
        } else {
            showNotification('Error: ' + data.error, 'error');
        }
    } catch (error) {
        hideLoading();
        showNotification('Error: ' + error.message, 'error');
        console.error('Image processing error:', error);
    }
}

async function handleTextSubmit(e) {
    e.preventDefault();

    const prescriptionText = document.getElementById('prescriptionText');
    const text = prescriptionText.value.trim();

    if (!text) {
        showNotification('Please enter prescription text', 'error');
        return;
    }

    // Show loading state
    showLoading('Processing text...');

    try {
        const response = await fetch('/api/process-text', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text: text })
        });

        const data = await response.json();

        hideLoading();

        if (data.success) {
            displayResults(data.data);
            showNotification('Analysis complete!', 'success');
        } else {
            showNotification('Error: ' + data.error, 'error');
        }
    } catch (error) {
        hideLoading();
        showNotification('Error: ' + error.message, 'error');
        console.error('Text processing error:', error);
    }
}

async function handleContactSubmit(e) {
    e.preventDefault();

    const formData = {
        name: document.getElementById('contactName').value,
        email: document.getElementById('contactEmail').value,
        message: document.getElementById('contactMessage').value
    };

    // Show loading
    showLoading('Sending message...');

    try {
        const response = await fetch('/api/contact', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(formData)
        });

        const data = await response.json();

        hideLoading();

        if (data.success) {
            showNotification('Message sent successfully!', 'success');
            document.getElementById('contactForm').reset();
        } else {
            showNotification('Error: ' + data.error, 'error');
        }
    } catch (error) {
        hideLoading();
        showNotification('Error: ' + error.message, 'error');
        console.error('Contact form error:', error);
    }
}

// ============================================================================
// RESULTS DISPLAY
// ============================================================================

function displayResults(data) {
    currentResults = data;

    // Update medications
    const medicationsEl = document.getElementById('medications');
    if (medicationsEl) {
        medicationsEl.innerHTML = (data.medications && data.medications.length)
            ? data.medications.map(m => `<li>${escapeHtml(m)}</li>`).join('')
            : '<li>None detected</li>';
    }

    // Update doses
    const dosesEl = document.getElementById('doses');
    if (dosesEl) {
        dosesEl.innerHTML = (data.doses && data.doses.length)
            ? data.doses.map(d => `<li>${escapeHtml(d)}</li>`).join('')
            : '<li>None detected</li>';
    }

    // Update routes
    const routesEl = document.getElementById('routes');
    if (routesEl) {
        routesEl.innerHTML = (data.routes && data.routes.length)
            ? data.routes.map(r => `<li>${escapeHtml(r)}</li>`).join('')
            : '<li>None detected</li>';
    }

    // Update frequencies
    const frequenciesEl = document.getElementById('frequencies');
    if (frequenciesEl) {
        frequenciesEl.innerHTML = (data.frequencies && data.frequencies.length)
            ? data.frequencies.map(f => `<li>${escapeHtml(f)}</li>`).join('')
            : '<li>None detected</li>';
    }

    // Update raw text
    const rawTextEl = document.getElementById('rawText');
    if (rawTextEl) {
        rawTextEl.textContent = data.raw_text || 'No text extracted';
    }

    // Show results section
    const resultsSection = document.getElementById('resultsSection');
    if (resultsSection) {
        resultsSection.style.display = 'block';
        resultsSection.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
}

function downloadResults() {
    if (!currentResults) {
        showNotification('No results to download', 'error');
        return;
    }

    const blob = new Blob([JSON.stringify(currentResults, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `prescription_analysis_${Date.now()}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);

    showNotification('Results downloaded!', 'success');
}

function copyResults() {
    if (!currentResults) {
        showNotification('No results to copy', 'error');
        return;
    }

    const text = JSON.stringify(currentResults, null, 2);

    navigator.clipboard.writeText(text)
        .then(() => showNotification('Results copied to clipboard!', 'success'))
        .catch(() => showNotification('Failed to copy results', 'error'));
}

function newAnalysis() {
    // Reset forms
    const imageForm = document.getElementById('imageForm');
    if (imageForm) imageForm.reset();

    const textForm = document.getElementById('textForm');
    if (textForm) textForm.reset();

    // Hide results
    const resultsSection = document.getElementById('resultsSection');
    if (resultsSection) resultsSection.style.display = 'none';

    // Reset drop zone text
    const dropZone = document.getElementById('dropZone');
    if (dropZone) {
        const textElement = dropZone.querySelector('p');
        if (textElement) {
            textElement.textContent = 'Click to upload or drag & drop';
        }
    }

    // Clear current results
    currentResults = null;

    // Scroll to top of upload section
    window.scrollTo({ top: 0, behavior: 'smooth' });

    showNotification('Ready for new analysis', 'success');
}

// ============================================================================
// DASHBOARD
// ============================================================================

function initializeDashboard() {
    // Check system health on dashboard load
    setInterval(() => {
        if (document.getElementById('dashboard')?.classList.contains('active')) {
            checkSystemHealth();
        }
    }, 30000); // Check every 30 seconds
}

async function checkSystemHealth() {
    try {
        const startTime = Date.now();
        const response = await fetch('/api/health');
        const responseTime = Date.now() - startTime;
        const data = await response.json();

        // Update frontend status
        updateStatus('frontend', 'online', 'Online');

        // Update backend status
        if (data.backend && data.backend.success) {
            updateStatus('backend', 'online', 'Online');

            const backendResponseEl = document.getElementById('backendResponse');
            if (backendResponseEl) {
                backendResponseEl.textContent = responseTime + 'ms';
            }

            // Update component statuses
            if (data.backend.data && data.backend.data.components) {
                const components = data.backend.data.components;

                // NER Model status
                const nerStatus = components.ner_model === 'initialized' ? 'online' : 'offline';
                updateStatus('ner', nerStatus, nerStatus === 'online' ? 'Online' : 'Offline');

                // Textract status
                const textractStatus = components.textract === 'configured' ? 'online' : 'offline';
                updateStatus('textract', textractStatus, textractStatus === 'online' ? 'Online' : 'Offline');
            }
        } else {
            updateStatus('backend', 'offline', 'Offline');
            updateStatus('ner', 'offline', 'Offline');
            updateStatus('textract', 'offline', 'Offline');
        }
    } catch (error) {
        console.error('Health check failed:', error);
        updateStatus('backend', 'offline', 'Offline');
        updateStatus('ner', 'offline', 'Offline');
        updateStatus('textract', 'offline', 'Offline');
    }
}

function updateStatus(component, status, text) {
    const statusEl = document.getElementById(component + 'Status');
    const statusTextEl = document.getElementById(component + 'StatusText');

    if (statusEl) {
        statusEl.className = 'status-indicator ' + status;
    }

    if (statusTextEl) {
        statusTextEl.textContent = text;
    }
}

function loadStats() {
    // In a real app, fetch from API
    const totalProcessedEl = document.getElementById('totalProcessed');
    const todayAnalysisEl = document.getElementById('todayAnalysis');

    if (totalProcessedEl) totalProcessedEl.textContent = '1,234';
    if (todayAnalysisEl) todayAnalysisEl.textContent = '47';
}

function updateUptime() {
    const uptimeEl = document.getElementById('frontendUptime');
    if (!uptimeEl) return;

    const elapsed = Math.floor((Date.now() - startTime) / 1000);
    const hours = Math.floor(elapsed / 3600);
    const minutes = Math.floor((elapsed % 3600) / 60);
    const seconds = elapsed % 60;

    uptimeEl.textContent = `${hours}h ${minutes}m ${seconds}s`;
}

// ============================================================================
// UI HELPERS
// ============================================================================

function showLoading(message = 'Loading...') {
    // Create loading overlay if it doesn't exist
    let overlay = document.getElementById('loadingOverlay');

    if (!overlay) {
        overlay = document.createElement('div');
        overlay.id = 'loadingOverlay';
        overlay.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0, 0, 0, 0.7);
            display: flex;
            align-items: center;
            justify-content: center;
            z-index: 9999;
        `;

        overlay.innerHTML = `
            <div style="text-align: center; color: white;">
                <div class="spinner" style="
                    width: 50px;
                    height: 50px;
                    border: 4px solid rgba(255,255,255,0.3);
                    border-top: 4px solid white;
                    border-radius: 50%;
                    animation: spin 1s linear infinite;
                    margin: 0 auto 1rem;
                "></div>
                <p id="loadingMessage">${message}</p>
            </div>
        `;

        document.body.appendChild(overlay);
    } else {
        const messageEl = document.getElementById('loadingMessage');
        if (messageEl) messageEl.textContent = message;
        overlay.style.display = 'flex';
    }
}

function hideLoading() {
    const overlay = document.getElementById('loadingOverlay');
    if (overlay) {
        overlay.style.display = 'none';
    }
}

function showNotification(message, type = 'info') {
    // Create notification element
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.style.cssText = `
        position: fixed;
        top: 100px;
        right: 20px;
        padding: 1rem 1.5rem;
        border-radius: 8px;
        background: ${type === 'success' ? '#10b981' : type === 'error' ? '#ef4444' : '#3b82f6'};
        color: white;
        font-weight: 500;
        box-shadow: 0 10px 25px rgba(0,0,0,0.3);
        z-index: 10000;
        animation: slideIn 0.3s ease-out;
        max-width: 400px;
    `;
    notification.textContent = message;

    document.body.appendChild(notification);

    // Remove after 3 seconds
    setTimeout(() => {
        notification.style.animation = 'slideOut 0.3s ease-out';
        setTimeout(() => notification.remove(), 300);
    }, 3000);
}

// ============================================================================
// UTILITY FUNCTIONS
// ============================================================================

function escapeHtml(text) {
    const map = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#039;'
    };
    return text.replace(/[&<>"']/g, m => map[m]);
}

// ============================================================================
// ANIMATIONS (Add to CSS)
// ============================================================================
/*
@keyframes spin {
    0% { transform: rotate(0deg); }
    100% { transform: rotate(360deg); }
}

@keyframes slideIn {
    from {
        transform: translateX(400px);
        opacity: 0;
    }
    to {
        transform: translateX(0);
        opacity: 1;
    }
}

@keyframes slideOut {
    from {
        transform: translateX(0);
        opacity: 1;
    }
    to {
        transform: translateX(400px);
        opacity: 0;
    }
}
*/

// ============================================================================
// EXPORT FUNCTIONS TO GLOBAL SCOPE
// ============================================================================

window.navigateToSection = navigateToSection;
window.downloadResults = downloadResults;
window.copyResults = copyResults;
window.newAnalysis = newAnalysis;
window.checkSystemHealth = checkSystemHealth;
window.loadStats = loadStats;

console.log('OCR Prescription Intelligence app.js loaded successfully');