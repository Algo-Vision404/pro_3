const API_BASE = "http://localhost:8000";

async function updateMetrics() {
    try {
        const res = await fetch(`${API_BASE}/metrics`);
        const data = await res.json();
        
        // Animate counting up for values if changed
        animateValue('stat-total', data.total_processed);
        animateValue('stat-resolved', data.resolved_count);
        animateValue('stat-escalated', data.escalated_count);
        
        const confidence = data.total_processed > 0 ? (data.avg_confidence || 0.85) : 0;
        document.getElementById('stat-confidence').innerText = `${Math.round(confidence * 100)}%`;
    } catch (e) {
        console.error("Failed to fetch metrics", e);
    }
}

function animateValue(id, target) {
    const el = document.getElementById(id);
    const current = parseInt(el.innerText) || 0;
    if (current !== target) {
        el.innerText = target;
        el.style.transform = 'scale(1.2)';
        el.style.color = 'var(--accent-primary)';
        setTimeout(() => {
            el.style.transform = 'scale(1)';
            el.style.color = '';
        }, 300);
    }
}

async function ingestDemoTicket() {
    const samples = [
        { user_id: "user_1", subject: "Urgent: Billing issue - double charge", body: "I was charged twice last night for my premium subscription. Please refund the second charge immediately as this caused an overdraft.", source: "email" },
        { user_id: "user_2", subject: "Login failed after reset", body: "I can't access my account after the password reset. The system keeps telling me invalid credentials even though I just changed it.", source: "api" },
        { user_id: "user_3", subject: "Feature request: Dark Mode", body: "Can we have a dark mode in the main app? The current UI is too bright for late night coding sessions.", source: "webhook" },
        { user_id: "user_4", subject: "API Rate limits exceeded", body: "My production application is getting 429 Too Many Requests errors, but my dashboard shows I have not exceeded my quota.", source: "api" },
        { user_id: "user_5", subject: "How to export data?", body: "I need to export all my activity logs to a CSV for compliance reasons. Where can I find this option?", source: "email" }
    ];
    
    const sample = samples[Math.floor(Math.random() * samples.length)];
    const btn = document.querySelector('.btn-primary');
    const originalText = btn.innerHTML;
    btn.innerHTML = 'Ingesting...';
    btn.disabled = true;

    try {
        const ingestRes = await fetch(`${API_BASE}/ingest_ticket`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(sample)
        });
        const ticket = await ingestRes.json();
        
        await fetch(`${API_BASE}/process_ticket/${ticket.ticket_id}?mode=assisted`, { method: 'POST' });
        
        await refreshList();
        await updateMetrics();
    } catch (e) {
        console.error(e);
        alert("Connection Error: Is the backend server running on port 8000?");
    } finally {
        btn.innerHTML = originalText;
        btn.disabled = false;
    }
}

async function refreshList() {
    try {
        const res = await fetch(`${API_BASE}/tickets`);
        const tickets = await res.json();
        renderList(tickets);
    } catch (e) {
        console.error("Failed to refresh list", e);
    }
}

function renderList(tickets) {
    const list = document.getElementById('ticket-list');
    list.innerHTML = '';
    
    if (tickets.length === 0) {
        list.innerHTML = `<div style="text-align: center; padding: 2rem; color: var(--text-muted);">No tickets in queue.</div>`;
        return;
    }

    tickets.reverse().forEach(t => {
        const item = document.createElement('div');
        item.className = 'ticket-item';
        item.onclick = () => viewTicket(t.ticket_id);
        
        const urgencyClass = t.urgency_score > 0.7 ? 'badge-high' : t.urgency_score > 0.3 ? 'badge-mid' : 'badge-low';
        const urgencyLabel = t.urgency_score > 0.7 ? 'CRITICAL' : t.urgency_score > 0.3 ? 'NORMAL' : 'LOW';
        
        let statusBadge = '';
        if (t.status === 'resolved') statusBadge = '<span class="badge badge-low">RESOLVED</span>';
        else if (t.status === 'escalated') statusBadge = '<span class="badge badge-high">ESCALATED</span>';
        else statusBadge = '<span class="badge badge-mid">PENDING</span>';

        item.innerHTML = `
            <div style="font-family: 'Outfit', sans-serif; font-size: 0.85rem; color: var(--text-muted)">#${t.ticket_id.slice(0, 6)}</div>
            <div>
                <div style="font-weight: 600; margin-bottom: 0.25rem;">${t.subject}</div>
                <div style="font-size: 0.75rem; color: var(--text-muted);">Intent Analysis Complete</div>
            </div>
            <div><span class="badge ${urgencyClass}">${urgencyLabel}</span></div>
            <div>${statusBadge}</div>
        `;
        list.appendChild(item);
    });
}

async function viewTicket(id) {
    try {
        const res = await fetch(`${API_BASE}/ticket/${id}`);
        const data = await res.json();
        
        const t = data.ticket;
        const p = data.processed_data;

        if (!p) {
            alert("Ticket is still being processed.");
            return;
        }

        document.getElementById('modal-subject').innerText = t.subject;
        document.getElementById('modal-body').innerText = t.body;
        document.getElementById('modal-intent').innerText = `Intent: ${p.classification.intent.replace('_', ' ').toUpperCase()}`;
        document.getElementById('modal-sentiment').innerText = `Sentiment: ${p.classification.sentiment.toUpperCase()}`;
        document.getElementById('ai-response-draft').value = p.draft.response_draft;
        
        const urgencyClass = p.classification.urgency_score > 0.7 ? 'badge-high' : p.classification.urgency_score > 0.3 ? 'badge-mid' : 'badge-low';
        const urgencyLabel = p.classification.urgency_score > 0.7 ? 'CRITICAL' : p.classification.urgency_score > 0.3 ? 'NORMAL' : 'LOW';
        const badgeEl = document.getElementById('modal-urgency-badge');
        badgeEl.className = `badge ${urgencyClass}`;
        badgeEl.innerText = urgencyLabel;

        const escalationAlert = document.getElementById('escalation-alert');
        if (p.escalation) {
            escalationAlert.style.display = 'block';
            document.getElementById('escalation-reason').innerText = p.escalation.issue_summary;
        } else {
            escalationAlert.style.display = 'none';
        }

        // Bind resolve button
        const resolveBtn = document.getElementById('btn-resolve');
        resolveBtn.onclick = () => resolveTicket(id);

        const overlay = document.getElementById('modal-overlay');
        overlay.style.display = 'flex';
        // Small delay to allow display:flex to apply before adding active class for transition
        setTimeout(() => overlay.classList.add('active'), 10);
    } catch(e) {
        console.error("Error viewing ticket", e);
    }
}

async function resolveTicket(id) {
    const editedResponse = document.getElementById('ai-response-draft').value;
    try {
        await fetch(`${API_BASE}/feedback`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                ticket_id: id,
                human_edited_response: editedResponse,
                resolution_status: "resolved",
                feedback_notes: "Human approved via cognitive dashboard"
            })
        });
        closeModal();
        await refreshList();
        await updateMetrics();
    } catch (e) {
        alert("Failed to resolve ticket");
    }
}

function closeModal() {
    const overlay = document.getElementById('modal-overlay');
    overlay.classList.remove('active');
    setTimeout(() => {
        overlay.style.display = 'none';
    }, 300); // match transition duration
}

// Sidebar logic
document.querySelectorAll('nav li').forEach(li => {
    li.onclick = () => {
        document.querySelector('nav li.active').classList.remove('active');
        li.classList.add('active');
    };
});

// Initial load
updateMetrics();
refreshList();
setInterval(updateMetrics, 5000);
