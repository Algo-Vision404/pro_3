const API_BASE = "http://localhost:8000";

async function updateMetrics() {
    try {
        const res = await fetch(`${API_BASE}/metrics`);
        const data = await res.json();
        document.getElementById('stat-total').innerText = data.total_processed;
        document.getElementById('stat-resolved').innerText = data.resolved_count;
        document.getElementById('stat-escalated').innerText = data.escalated_count;
        const confidence = data.total_processed > 0 ? (data.avg_confidence || 0.85) : 0;
        document.getElementById('stat-confidence').innerText = `${Math.round(confidence * 100)}%`;
    } catch (e) {
        console.error("Failed to fetch metrics", e);
    }
}

async function ingestDemoTicket() {
    const samples = [
        { user_id: "user_1", subject: "Urgent: Billing issue", body: "I was charged twice twice last night. Please refund immediately.", source: "email" },
        { user_id: "user_2", subject: "Login failed", body: "I can't access my account after the password reset. Help!", source: "api" },
        { user_id: "user_3", subject: "Feature request", body: "Can we have a dark mode in the main app?", source: "webhook" }
    ];
    
    const sample = samples[Math.floor(Math.random() * samples.length)];
    const btn = document.querySelector('.btn-primary');
    const originalText = btn.innerText;
    btn.innerText = "Ingesting...";
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
        btn.innerText = "Ingest Sample Ticket";
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
    
    tickets.reverse().forEach(t => {
        const item = document.createElement('div');
        item.className = 'ticket-item';
        item.onclick = () => viewTicket(t.ticket_id);
        
        const urgencyClass = t.urgency_score > 0.7 ? 'badge-high' : t.urgency_score > 0.3 ? 'badge-mid' : 'badge-low';
        const urgencyLabel = t.urgency_score > 0.7 ? 'High' : t.urgency_score > 0.3 ? 'Medium' : 'Low';
        
        item.innerHTML = `
            <div style="font-size: 0.7rem; color: var(--text-muted)">#${t.ticket_id.slice(0, 8)}</div>
            <div style="font-weight: 600">${t.subject}</div>
            <div><span class="badge ${urgencyClass}">${urgencyLabel}</span></div>
            <div><span class="badge" style="background: rgba(255,255,255,0.1)">${t.status.toUpperCase()}</span></div>
        `;
        list.appendChild(item);
    });
}

async function viewTicket(id) {
    const res = await fetch(`${API_BASE}/ticket/${id}`);
    const data = await res.json();
    
    const t = data.ticket;
    const p = data.processed_data;

    document.getElementById('modal-subject').innerText = t.subject;
    document.getElementById('modal-body').innerText = t.body;
    document.getElementById('modal-intent').innerText = `Intent: ${p.classification.intent.replace('_', ' ')}`;
    document.getElementById('modal-sentiment').innerText = `Sentiment: ${p.classification.sentiment}`;
    document.getElementById('ai-response-draft').value = p.draft.response_draft;
    
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

    document.getElementById('modal-overlay').style.display = 'flex';
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
                feedback_notes: "Human approved via dashboard"
            })
        });
        closeModal();
        refreshList();
        updateMetrics();
    } catch (e) {
        alert("Failed to resolve ticket");
    }
}

function closeModal() {
    document.getElementById('modal-overlay').style.display = 'none';
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
