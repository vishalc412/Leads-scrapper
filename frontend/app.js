// API Configuration
const API_BASE_URL = window.location.hostname === 'localhost' && window.location.port !== '80'
    ? 'http://localhost:8000'
    : '/api';

// State
let currentLeads = [];

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    setupEventListeners();
    checkAPIHealth();
});

function setupEventListeners() {
    const form = document.getElementById('searchForm');
    form.addEventListener('submit', handleSearch);
}

// API Health Check
async function checkAPIHealth() {
    try {
        const response = await fetch(`${API_BASE_URL}/health`);
        const data = await response.json();
        console.log('API Health:', data);
    } catch (error) {
        console.error('API not reachable:', error);
        showAlert('API backend is not reachable. Please ensure the backend is running.', 'error');
    }
}

// Search Handler
async function handleSearch(e) {
    e.preventDefault();

    const keywords = document.getElementById('keywords').value.split(',').map(k => k.trim());
    const city = document.getElementById('city').value;
    const state = document.getElementById('state').value;
    const maxResults = parseInt(document.getElementById('maxResults').value);
    const remote = document.getElementById('remote').checked;

    const query = {
        keywords,
        location: {
            city: city || null,
            state: state || null,
            country: "US",
            remote
        },
        max_results: maxResults
    };

    await searchLeads(query);
}

// Search Leads API Call
async function searchLeads(query) {
    const searchBtn = document.getElementById('searchBtn');
    const btnText = searchBtn.querySelector('.btn-text');
    const spinner = searchBtn.querySelector('.spinner');

    // Show loading state
    searchBtn.disabled = true;
    btnText.textContent = 'Searching...';
    spinner.style.display = 'inline-block';

    try {
        const response = await fetch(`${API_BASE_URL}/search`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                query,
                save_results: true,
                parallel: true,
                deduplicate: true
            })
        });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const data = await response.json();
        currentLeads = data.leads || [];

        displayResults(data);
        showAlert(`Found ${data.total_scraped} leads in ${data.execution_time.toFixed(2)}s`, 'success');

    } catch (error) {
        console.error('Search error:', error);
        showAlert(`Search failed: ${error.message}`, 'error');
    } finally {
        // Reset button state
        searchBtn.disabled = false;
        btnText.textContent = 'Search Leads';
        spinner.style.display = 'none';
    }
}

// Display Results
function displayResults(data) {
    const section = document.getElementById('resultsSection');
    const container = document.getElementById('resultsContainer');
    const stats = document.getElementById('resultsStats');

    section.style.display = 'block';
    stats.textContent = `${data.total_scraped} leads found • ${data.execution_time.toFixed(2)}s`;

    if (data.leads.length === 0) {
        container.innerHTML = '<p class="text-muted">No leads found. Try different search criteria.</p>';
        return;
    }

    container.innerHTML = data.leads.map(lead => createLeadCard(lead)).join('');
}

// Create Lead Card HTML
function createLeadCard(lead) {
    const badgeClass = `badge-${lead.source}`;
    const location = formatLocation(lead.location);
    const salary = formatSalary(lead);
    const skills = lead.required_skills?.slice(0, 5).join(', ') || 'Not specified';

    return `
        <div class="lead-card" data-id="${lead.id}">
            <div class="lead-header">
                <div>
                    <div class="lead-title">${escapeHtml(lead.title)}</div>
                    <div class="lead-company">${escapeHtml(lead.company.name)}</div>
                </div>
                <span class="lead-badge ${badgeClass}">${lead.source}</span>
            </div>

            <div class="lead-details">
                <div class="lead-detail">
                    <span>📍</span>
                    <span>${location}</span>
                </div>
                ${salary ? `
                <div class="lead-detail">
                    <span>💰</span>
                    <span>${salary}</span>
                </div>
                ` : ''}
                <div class="lead-detail">
                    <span>🛠️</span>
                    <span>${escapeHtml(skills)}</span>
                </div>
            </div>

            <div class="lead-actions">
                <button class="btn btn-secondary btn-small" onclick="openLink('${lead.url}')">
                    View Job
                </button>
                <button class="btn btn-secondary btn-small" onclick="analyzeLead('${lead.id}')">
                    Analyze with AI
                </button>
            </div>
        </div>
    `;
}

// Load Saved Leads
async function loadSavedLeads() {
    const container = document.getElementById('savedLeadsContainer');
    container.innerHTML = '<p class="text-muted">Loading...</p>';

    try {
        const response = await fetch(`${API_BASE_URL}/leads?page=1&page_size=20`);

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }

        const data = await response.json();

        if (data.leads.length === 0) {
            container.innerHTML = '<p class="text-muted">No saved leads yet. Search for leads to get started!</p>';
            return;
        }

        container.innerHTML = data.leads.map(lead => createLeadCard(lead)).join('');

    } catch (error) {
        console.error('Load error:', error);
        container.innerHTML = `<p class="text-muted">Error loading leads: ${error.message}</p>`;
    }
}

// Analyze Lead
async function analyzeLead(leadId) {
    const section = document.getElementById('analysisSection');
    const container = document.getElementById('analysisContainer');

    section.style.display = 'block';
    container.innerHTML = '<p class="text-muted">Analyzing with AI... This may take a moment.</p>';

    try {
        const response = await fetch(`${API_BASE_URL}/analyze`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                lead_ids: [leadId]
            })
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Analysis failed');
        }

        const data = await response.json();

        if (data.analyses.length > 0) {
            displayAnalysis(data.analyses[0]);
        }

    } catch (error) {
        console.error('Analysis error:', error);
        container.innerHTML = `
            <div class="alert alert-error">
                Analysis failed: ${error.message}
                <br><small>Make sure you have configured an AI API key (ANTHROPIC_API_KEY or OPENAI_API_KEY)</small>
            </div>
        `;
    }
}

// Display Analysis
function displayAnalysis(analysis) {
    const container = document.getElementById('analysisContainer');

    const html = `
        <div class="card" style="background: #f8fafc; margin-top: 20px;">
            <h3 style="margin-bottom: 15px;">AI Analysis Results</h3>

            <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 15px; margin-bottom: 20px;">
                <div>
                    <div style="font-size: 0.875rem; color: var(--text-secondary);">Relevance Score</div>
                    <div style="font-size: 1.5rem; font-weight: 600; color: var(--primary-color);">
                        ${analysis.relevance_score.toFixed(0)}/100
                    </div>
                </div>
                <div>
                    <div style="font-size: 0.875rem; color: var(--text-secondary);">Match Score</div>
                    <div style="font-size: 1.5rem; font-weight: 600; color: var(--success-color);">
                        ${analysis.match_score.toFixed(0)}/100
                    </div>
                </div>
                <div>
                    <div style="font-size: 0.875rem; color: var(--text-secondary);">Quality Score</div>
                    <div style="font-size: 1.5rem; font-weight: 600; color: var(--secondary-color);">
                        ${analysis.quality_score.toFixed(0)}/100
                    </div>
                </div>
            </div>

            <div style="margin-bottom: 15px;">
                <strong>Summary:</strong>
                <p style="margin-top: 8px; color: var(--text-secondary);">${escapeHtml(analysis.summary)}</p>
            </div>

            ${analysis.key_highlights.length > 0 ? `
            <div style="margin-bottom: 15px;">
                <strong>Key Highlights:</strong>
                <ul style="margin-top: 8px; padding-left: 20px;">
                    ${analysis.key_highlights.map(h => `<li>${escapeHtml(h)}</li>`).join('')}
                </ul>
            </div>
            ` : ''}

            ${analysis.concerns.length > 0 ? `
            <div style="margin-bottom: 15px;">
                <strong>Concerns:</strong>
                <ul style="margin-top: 8px; padding-left: 20px; color: var(--danger-color);">
                    ${analysis.concerns.map(c => `<li>${escapeHtml(c)}</li>`).join('')}
                </ul>
            </div>
            ` : ''}

            <div style="font-size: 0.75rem; color: var(--text-secondary); margin-top: 15px;">
                Model: ${analysis.model_used} • Analyzed: ${new Date(analysis.analyzed_at).toLocaleString()}
            </div>
        </div>
    `;

    container.innerHTML = html;
}

// Utility Functions
function formatLocation(location) {
    const parts = [];
    if (location.city) parts.push(location.city);
    if (location.state) parts.push(location.state);
    if (location.remote) parts.push('(Remote)');
    return parts.join(', ') || 'Not specified';
}

function formatSalary(lead) {
    if (!lead.salary_min && !lead.salary_max) return null;

    const currency = lead.salary_currency || 'USD';
    if (lead.salary_min && lead.salary_max && lead.salary_min !== lead.salary_max) {
        return `${currency} ${lead.salary_min.toLocaleString()} - ${lead.salary_max.toLocaleString()}`;
    } else if (lead.salary_min) {
        return `${currency} ${lead.salary_min.toLocaleString()}+`;
    }
    return null;
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function openLink(url) {
    window.open(url, '_blank');
}

function showAlert(message, type = 'info') {
    // Simple alert - could be enhanced with a toast notification
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type}`;
    alertDiv.textContent = message;

    const container = document.querySelector('.main-content');
    container.insertBefore(alertDiv, container.firstChild);

    setTimeout(() => alertDiv.remove(), 5000);
}
