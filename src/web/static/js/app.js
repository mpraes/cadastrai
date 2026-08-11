let jwtToken = null;
let currentUser = null;

// Auth logic
async function login(username, password) {
    const errorDiv = document.getElementById('login-error');
    errorDiv.innerText = "Conectando...";
    
    try {
        const res = await fetch('/api/auth/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, password })
        });
        
        if (!res.ok) throw new Error("Falha no login");
        const data = await res.json();
        jwtToken = data.access_token;
        
        // fetch me
        const meRes = await fetch(`/api/auth/me?token=${jwtToken}`);
        currentUser = await meRes.json();
        
        // update UI
        document.getElementById('login-modal').classList.remove('active');
        document.getElementById('app-content').style.display = 'flex';
        
        document.getElementById('user-name').innerText = currentUser.username;
        document.getElementById('user-avatar').innerText = currentUser.username.charAt(0).toUpperCase();
        document.getElementById('dept-badge').innerText = currentUser.departamento;
        
        // Update greeting with user's name
        let displayName = currentUser.username.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
        document.getElementById('chat-messages').innerHTML = `
            <div class="message system-message">
                <div class="message-content">
                    <p>Olá, <strong>${displayName}</strong>! Sou o <strong>CadastrAÍ</strong>, seu assistente virtual. Posso te ajudar a cadastrar e consultar clientes no sistema.</p>
                    <p>O que você deseja fazer hoje?</p>
                </div>
            </div>
        `;
        
        switchView('chat');
        
    } catch (err) {
        errorDiv.innerText = "Usuário ou senha inválidos.";
        console.error(err);
    }
}

function handleLoginSubmit(event) {
    event.preventDefault();
    const username = document.getElementById('username').value.trim();
    const password = document.getElementById('password').value.trim();
    if (username && password) {
        login(username, password);
    }
}

function logout() {
    jwtToken = null;
    currentUser = null;
    document.getElementById('login-modal').classList.add('active');
    document.getElementById('app-content').style.display = 'none';
    document.getElementById('chat-messages').innerHTML = `
        <div class="message system-message">
            <div class="message-content">
                <p>Olá! Sou o <strong>CadastrAÍ</strong>, seu assistente virtual. Posso te ajudar a cadastrar e consultar clientes no sistema.</p>
                <p>O que você deseja fazer hoje?</p>
            </div>
        </div>
    `;
}

function clearChatUI() {
    let displayName = currentUser ? currentUser.username.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase()) : "";
    let greeting = displayName ? `Olá, <strong>${displayName}</strong>!` : `Olá!`;
    
    document.getElementById('chat-messages').innerHTML = `
        <div class="message system-message">
            <div class="message-content">
                <p>${greeting} Sou o <strong>CadastrAÍ</strong>, seu assistente virtual. Posso te ajudar a cadastrar e consultar clientes no sistema.</p>
                <p>O que você deseja fazer hoje?</p>
                <p><small><em>(A tela foi limpa, mas o agente ainda recorda o contexto da conversa.)</em></small></p>
            </div>
        </div>
    `;
}

// Chat logic
document.addEventListener('DOMContentLoaded', () => {
    const messageInput = document.getElementById('message-input');
    const sendBtn = document.getElementById('send-btn');
    const chatMessages = document.getElementById('chat-messages');

    messageInput.addEventListener('input', function() {
        this.style.height = 'auto';
        this.style.height = (this.scrollHeight) + 'px';
        sendBtn.disabled = this.value.trim() === '';
    });

    messageInput.addEventListener('keydown', function(e) {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });

    sendBtn.addEventListener('click', sendMessage);

    async function sendMessage() {
        const text = messageInput.value.trim();
        if (!text) return;

        addMessage(text, 'user-message');
        
        messageInput.value = '';
        messageInput.style.height = 'auto';
        sendBtn.disabled = true;
        scrollToBottom();

        const typingId = showTypingIndicator();
        scrollToBottom();

        try {
            const response = await fetch('/api/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${jwtToken}`
                },
                body: JSON.stringify({ message: text })
            });

            const data = await response.json();
            removeTypingIndicator(typingId);

            if (response.ok) {
                addMessage(data.response, 'bot-message');
                
                // Smart Table renderer
                if (data.structured_results && data.structured_results.length > 0) {
                    renderSmartTable(data.structured_results);
                }
                
                // Human-in-the-loop confirmation
                if (data.pending_confirmation) {
                    renderConfirmationCard(data.pending_confirmation);
                }
                
            } else {
                addMessage("Desculpe, ocorreu um erro na comunicação.", 'bot-message', true);
            }
        } catch (error) {
            removeTypingIndicator(typingId);
            addMessage("Erro de conexão.", 'bot-message', true);
        }
        
        scrollToBottom();
    }

    function addMessage(text, className, isError = false) {
        const msgDiv = document.createElement('div');
        msgDiv.className = `message ${className}`;
        
        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content';
        if (isError) {
            contentDiv.style.border = '1px solid #e53935';
            contentDiv.style.backgroundColor = '#ffebee';
        }

        let formattedText = text
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/\n/g, '<br>')
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
            
        contentDiv.innerHTML = formattedText;
        msgDiv.appendChild(contentDiv);
        chatMessages.appendChild(msgDiv);
    }
    
    function renderSmartTable(results) {
        const tableContainer = document.createElement('div');
        tableContainer.className = 'smart-table-container';
        
        const table = document.createElement('table');
        table.className = 'smart-table';
        
        const thead = document.createElement('thead');
        const headerRow = document.createElement('tr');
        
        const columns = Object.keys(results[0]);
        columns.forEach(col => {
            const th = document.createElement('th');
            th.innerText = col.replace('_', ' ').toUpperCase();
            headerRow.appendChild(th);
        });
        thead.appendChild(headerRow);
        table.appendChild(thead);
        
        const tbody = document.createElement('tbody');
        results.forEach(row => {
            const tr = document.createElement('tr');
            columns.forEach(col => {
                const td = document.createElement('td');
                td.innerText = row[col] || '-';
                tr.appendChild(td);
            });
            tbody.appendChild(tr);
        });
        table.appendChild(tbody);
        
        tableContainer.appendChild(table);
        chatMessages.appendChild(tableContainer);
    }
    
    function renderConfirmationCard(dados) {
        const cardId = 'confirm-card-' + Date.now();
        const card = document.createElement('div');
        card.className = 'confirmation-card';
        card.id = cardId;
        
        const title = document.createElement('h3');
        title.innerText = 'Revise os Dados para Cadastro';
        card.appendChild(title);
        
        const dataList = document.createElement('div');
        dataList.className = 'data-list';
        
        Object.keys(dados).forEach(key => {
            const item = document.createElement('div');
            item.className = 'data-item';
            item.innerHTML = `<strong>${key}:</strong> <span>${dados[key]}</span>`;
            dataList.appendChild(item);
        });
        card.appendChild(dataList);
        
        const actions = document.createElement('div');
        actions.className = 'card-actions';
        
        const confirmBtn = document.createElement('button');
        confirmBtn.className = 'btn btn-primary';
        confirmBtn.innerText = 'Confirmar Cadastro';
        confirmBtn.onclick = () => sendConfirmation(dados, cardId);
        
        const cancelBtn = document.createElement('button');
        cancelBtn.className = 'btn btn-secondary';
        cancelBtn.innerText = 'Cancelar';
        cancelBtn.onclick = () => {
            document.getElementById(cardId).innerHTML = '<p class="text-secondary">Cadastro cancelado.</p>';
        };
        
        actions.appendChild(cancelBtn);
        actions.appendChild(confirmBtn);
        card.appendChild(actions);
        
        chatMessages.appendChild(card);
    }
    
    async function sendConfirmation(dados, cardId) {
        const card = document.getElementById(cardId);
        card.style.opacity = '0.5';
        
        try {
            const res = await fetch('/api/confirm_registration', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${jwtToken}`
                },
                body: JSON.stringify({ dados })
            });
            const result = await res.json();
            
            if (res.ok) {
                card.innerHTML = `<p style="color: #007833; font-weight: 500;">✅ ${result.message}</p>`;
            } else {
                card.innerHTML = `<p style="color: #e53935; font-weight: 500;">❌ Erro: ${result.detail}</p>`;
            }
        } catch (e) {
            card.innerHTML = `<p style="color: #e53935; font-weight: 500;">❌ Falha na conexão.</p>`;
        }
        card.style.opacity = '1';
    }

    function showTypingIndicator() {
        const id = 'typing-' + Date.now();
        const indicator = document.createElement('div');
        indicator.id = id;
        indicator.className = 'typing-indicator';
        indicator.innerHTML = `<div class="typing-dot"></div><div class="typing-dot"></div><div class="typing-dot"></div>`;
        chatMessages.appendChild(indicator);
        return id;
    }

    function removeTypingIndicator(id) {
        const indicator = document.getElementById(id);
        if (indicator) indicator.remove();
    }

    function scrollToBottom() {
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }
});

// View switching logic
function switchView(viewName) {
    const chatContainer = document.querySelector('.chat-container');
    const dashboardContainer = document.getElementById('dashboard-container');
    const navChat = document.getElementById('nav-chat');
    const navDashboard = document.getElementById('nav-dashboard');

    if (viewName === 'chat') {
        chatContainer.style.display = 'flex';
        dashboardContainer.style.display = 'none';
        navChat.classList.add('active');
        navDashboard.classList.remove('active');
    } else if (viewName === 'dashboard') {
        chatContainer.style.display = 'none';
        dashboardContainer.style.display = 'flex';
        navChat.classList.remove('active');
        navDashboard.classList.add('active');
        fetchDashboardData();
    }
}

// Fetch and render dashboard
async function fetchDashboardData() {
    try {
        const res = await fetch('/api/dashboard/kpis', {
            headers: { 'Authorization': `Bearer ${jwtToken}` }
        });
        if (!res.ok) throw new Error("Erro ao carregar dados do dashboard");
        const data = await res.json();
        renderDashboard(data);
    } catch (err) {
        console.error(err);
    }
}

function renderDashboard(data) {
    document.getElementById('kpi-total-clients').innerText = data.total_clients;
    document.getElementById('kpi-current-dept').innerText = currentUser.departamento;

    // Render bar chart for departments
    const chartContainer = document.getElementById('chart-container');
    chartContainer.innerHTML = '';
    
    // Find max count for relative width
    const maxCount = Math.max(...data.clients_by_department.map(d => d.count), 1);
    
    data.clients_by_department.forEach(d => {
        const wrap = document.createElement('div');
        wrap.className = 'chart-bar-wrap';
        
        const label = document.createElement('div');
        label.className = 'chart-label';
        label.innerText = d.departamento;
        label.title = d.departamento;
        
        const bg = document.createElement('div');
        bg.className = 'chart-bar-bg';
        
        const fill = document.createElement('div');
        fill.className = 'chart-bar-fill';
        const percent = (d.count / maxCount) * 100;
        fill.style.width = `${percent}%`;
        
        bg.appendChild(fill);
        
        const val = document.createElement('div');
        val.className = 'chart-val';
        val.innerText = d.count;
        
        wrap.appendChild(label);
        wrap.appendChild(bg);
        wrap.appendChild(val);
        chartContainer.appendChild(wrap);
    });

    // Render recent clients
    const recentList = document.getElementById('recent-clients-list');
    recentList.innerHTML = '';
    
    if (data.recent_clients.length === 0) {
        recentList.innerHTML = '<p class="text-secondary">Nenhum cliente recente encontrado.</p>';
    } else {
        data.recent_clients.forEach(c => {
            const item = document.createElement('div');
            item.className = 'recent-client-item';
            
            const dateStr = c.data_cadastro ? new Date(c.data_cadastro).toLocaleDateString('pt-BR') : '-';
            
            item.innerHTML = `
                <div>
                    <div class="rc-name">${c.razao_social || 'Sem Nome'}</div>
                    <div class="rc-dept">${c.departamento}</div>
                </div>
                <div class="rc-date">${dateStr}</div>
            `;
            recentList.appendChild(item);
        });
    }
}
