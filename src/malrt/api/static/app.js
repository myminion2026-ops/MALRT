/* MALRT Dashboard — app.js */

const API = '/api';
let selectedSubmissionId = null;

// --- Init ---
document.addEventListener('DOMContentLoaded', () => {
    loadProviders();
    loadSubmissions();
    setupForm();
    setupSSE();
    setupDetailClose();
});

// --- Providers ---
async function loadProviders() {
    try {
        const res = await fetch(`${API}/providers`);
        const providers = await res.json();
        const el = document.getElementById('providers');
        el.innerHTML = providers.map(p => `
            <div class="provider-badge ${p.enabled ? 'enabled' : 'disabled'}">
                <span class="dot"></span>
                ${p.name}
            </div>
        `).join('');
    } catch (e) {
        console.error('Failed to load providers:', e);
    }
}

// --- Submit ---
function setupForm() {
    const form = document.getElementById('submit-form');
    const input = document.getElementById('indicator-input');
    const notesInput = document.getElementById('notes-input');
    const btn = document.getElementById('submit-btn');

    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        const value = input.value.trim();
        if (!value) return;

        const notes = notesInput.value.trim();
        btn.disabled = true;
        btn.textContent = 'Submitting...';

        try {
            const res = await fetch(`${API}/submit`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ indicator: value, notes }),
            });
            if (!res.ok) throw new Error(await res.text());
            input.value = '';
            notesInput.value = '';
            await loadSubmissions();
        } catch (e) {
            alert(`Submit failed: ${e.message}`);
        } finally {
            btn.disabled = false;
            btn.textContent = 'Submit';
        }
    });
}

// --- Submissions list ---
async function loadSubmissions() {
    try {
        const res = await fetch(`${API}/submissions`);
        const subs = await res.json();
        renderSubmissions(subs);
    } catch (e) {
        console.error('Failed to load submissions:', e);
    }
}

function renderSubmissions(subs) {
    const tbody = document.getElementById('submissions-body');
    const empty = document.getElementById('empty-state');

    if (!subs.length) {
        tbody.innerHTML = '';
        empty.style.display = 'block';
        return;
    }

    empty.style.display = 'none';
    tbody.innerHTML = subs.map(s => `
        <tr data-id="${s.id}" onclick="showDetail('${s.id}')">
            <td><code>${escapeHtml(s.indicator.value)}</code>${s.notes ? '<span class="notes-icon" title="Has notes">📝</span>' : ''}</td>
            <td><span class="type-badge">${s.indicator.type}</span></td>
            <td><span class="status ${s.status}">${s.status}</span></td>
            <td>${s.results.length} provider${s.results.length !== 1 ? 's' : ''}</td>
            <td>${formatTime(s.created_at)}</td>
        </tr>
    `).join('');
}

// --- Detail panel ---
async function showDetail(id) {
    selectedSubmissionId = id;
    try {
        const res = await fetch(`${API}/submissions/${id}`);
        const sub = await res.json();

        document.getElementById('detail-title').textContent =
            `${sub.indicator.type.toUpperCase()}: ${sub.indicator.value}`;

        const content = document.getElementById('detail-content');
        let notesHtml = `
            <div class="notes-section">
                <label>Notes</label>
                <textarea id="detail-notes" placeholder="Add notes...">${escapeHtml(sub.notes || '')}</textarea>
                <button class="notes-save-btn" onclick="saveNotes('${sub.id}')">Save Notes</button>
            </div>
        `;
        if (!sub.results.length) {
            content.innerHTML = notesHtml + '<div class="empty-state">No provider results yet.</div>';
        } else {
            content.innerHTML = notesHtml + sub.results.map(r => `
                <div class="result-card">
                    <div class="provider-name">
                        ${r.provider}
                        <span class="status ${r.status}">${r.status}</span>
                    </div>
                    ${r.error ? `<div style="color:var(--red);font-size:0.85rem;">${escapeHtml(r.error)}</div>` : ''}
                    ${r.response_data ? `<pre>${escapeHtml(JSON.stringify(r.response_data, null, 2))}</pre>` : ''}
                </div>
            `).join('');
        }

        document.getElementById('detail-panel').classList.add('open');
    } catch (e) {
        console.error('Failed to load detail:', e);
    }
}

function setupDetailClose() {
    document.getElementById('detail-close').addEventListener('click', () => {
        document.getElementById('detail-panel').classList.remove('open');
        selectedSubmissionId = null;
    });
}

// --- Save notes ---
async function saveNotes(id) {
    const textarea = document.getElementById('detail-notes');
    const notes = textarea.value;
    try {
        const res = await fetch(`${API}/submissions/${id}/notes`, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ notes }),
        });
        if (!res.ok) throw new Error(await res.text());
        await loadSubmissions();
    } catch (e) {
        alert(`Failed to save notes: ${e.message}`);
    }
}

// --- SSE (live updates) ---
function setupSSE() {
    const es = new EventSource(`${API}/stream`);
    es.onmessage = (event) => {
        try {
            const subs = JSON.parse(event.data);
            renderSubmissions(subs);
            // Refresh detail if viewing one
            if (selectedSubmissionId) {
                showDetail(selectedSubmissionId);
            }
        } catch (e) {
            console.error('SSE parse error:', e);
        }
    };
    es.onerror = () => {
        console.warn('SSE disconnected, will auto-reconnect');
    };
}

// --- Helpers ---
function escapeHtml(str) {
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}

function formatTime(iso) {
    if (!iso) return '—';
    const d = new Date(iso);
    return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
}
