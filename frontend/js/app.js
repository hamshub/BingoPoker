/**
 * app.js - BingoPoker main application logic
 * 
 * Manages state, screen navigation, and user interactions
 */

// ===== Global State =====

const appState = {
    currentUser: null,
    currentRoom: null,
    selectedPokerValue: null,
    selectedBingoCells: new Set(),  // "row-col" strings owned by this user
    rooms: [],
    currentGrid: null,
    ws: null,  // active WebSocket connection
};

// ===== Screen Management =====

function showScreen(screenId) {
    document.querySelectorAll('.screen').forEach(s => s.classList.remove('active'));
    const screen = document.getElementById(screenId);
    if (screen) {
        screen.classList.add('active');
    }
}

function showLoading(show = true) {
    const spinner = document.getElementById('loadingSpinner');
    if (show) {
        spinner.classList.remove('hidden');
    } else {
        spinner.classList.add('hidden');
    }
}

function showLoginModal() {
    document.getElementById('loginModal')?.classList.remove('hidden');
}

function hideLoginModal() {
    document.getElementById('loginModal')?.classList.add('hidden');
}

function showError(containerId, message) {
    const errorEl = document.getElementById(containerId);
    if (errorEl) {
        errorEl.textContent = message;
        errorEl.classList.remove('hidden');
    }
}

function hideError(containerId) {
    const errorEl = document.getElementById(containerId);
    if (errorEl) {
        errorEl.classList.add('hidden');
    }
}

// ===== Initialization =====

document.addEventListener('DOMContentLoaded', function() {
    if (new URLSearchParams(location.search).get('dev') === 'true') {
        document.getElementById('devTools')?.classList.remove('hidden');
    }
    setupEventListeners();
    checkAuthStatus();
});

window.addEventListener('popstate', function() {
    const urlRoom = new URLSearchParams(location.search).get('r');
    if (!urlRoom && appState.currentRoom) {
        // Back from room → room list
        if (appState.ws) { appState.ws.close(); appState.ws = null; }
        appState.currentRoom = null;
        appState.selectedBingoCells.clear();
        appState.selectedPokerValue = null;
        showScreen('roomSelectScreen');
        loadRooms();
    } else if (urlRoom && appState.currentUser) {
        joinRoom(urlRoom);
    }
});

function checkAuthStatus() {
    const savedUser = localStorage.getItem('bingopoker_user');
    const pendingRoom = sessionStorage.getItem('pending_room');
    const urlRoom = new URLSearchParams(location.search).get('r');

    if (savedUser) {
        try {
            appState.currentUser = JSON.parse(savedUser);
            showScreen('roomSelectScreen');
            if (!appState.currentUser.user_id) {
                refreshStoredUser();
            }
            loadRooms();
            updateUserDisplay();

            // Auto-join room from URL or pending redirect after login
            const roomToJoin = urlRoom || pendingRoom;
            if (roomToJoin) {
                sessionStorage.removeItem('pending_room');
                joinRoom(roomToJoin);
            }
        } catch (e) {
            localStorage.removeItem('bingopoker_user');
            showScreen('roomSelectScreen');
            showLoginModal();
        }
    } else {
        // Save intended room so we can redirect back after login
        if (urlRoom) {
            sessionStorage.setItem('pending_room', urlRoom);
        }
        showScreen('roomSelectScreen');
        showLoginModal();
    }
}

// Upgrades sessions stored before user IDs were introduced
async function refreshStoredUser() {
    const result = await BingoPokerAPI.getUser(appState.currentUser.email);
    if (result.success) {
        appState.currentUser = { ...appState.currentUser, ...result.data.user };
        localStorage.setItem('bingopoker_user', JSON.stringify(appState.currentUser));
        loadRooms();
    }
}

function setupEventListeners() {
    // Registration form
    const registerForm = document.getElementById('registerForm');
    if (registerForm) {
        registerForm.addEventListener('submit', handleRegister);
    }
    
    // Create room form
    const createRoomForm = document.getElementById('createRoomForm');
    if (createRoomForm) {
        createRoomForm.addEventListener('submit', handleCreateRoom);
    }
    
    // Role swap button
    const roleSwapBtn = document.getElementById('roleSwapBtn');
    if (roleSwapBtn) {
        roleSwapBtn.addEventListener('click', handleRoleSwap);
    }
    
    // Logout button
    const logoutBtn = document.getElementById('logoutBtn');
    if (logoutBtn) {
        logoutBtn.addEventListener('click', handleLogout);
    }
    
    // Leave room button
    const leaveRoomBtn = document.getElementById('leaveRoomBtn');
    if (leaveRoomBtn) {
        leaveRoomBtn.addEventListener('click', handleLeaveRoom);
    }
    
    // Download grid button
    const downloadGridBtn = document.getElementById('downloadGridBtn');
    if (downloadGridBtn) {
        downloadGridBtn.addEventListener('click', handleDownloadGrid);
    }
    
    // Reveal/Reset buttons
    const revealBtn = document.getElementById('revealBtn');
    if (revealBtn) {
        revealBtn.addEventListener('click', handleReveal);
    }
    
    const resetBtn = document.getElementById('resetBtn');
    if (resetBtn) {
        resetBtn.addEventListener('click', handleReset);
    }
}

// ===== Authentication =====

async function handleRegister(e) {
    e.preventDefault();
    
    const email = document.getElementById('emailInput').value.trim();
    const username = document.getElementById('usernameInput').value.trim();
    const role = document.getElementById('roleInput').value;

    if (!email || !username) {
        showError('registerError', 'Email and username are required');
        return;
    }

    showLoading(true);
    const result = await BingoPokerAPI.registerUser(email, username, role);
    showLoading(false);
    
    if (result.success) {
        const user = result.data.user;
        appState.currentUser = user;
        localStorage.setItem('bingopoker_user', JSON.stringify(user));
        
        document.getElementById('registerForm').reset();
        hideError('registerError');
        hideLoginModal();

        const pendingRoom = sessionStorage.getItem('pending_room');
        if (pendingRoom) {
            sessionStorage.removeItem('pending_room');
            await joinRoom(pendingRoom);
        } else {
            showScreen('roomSelectScreen');
            updateUserDisplay();
            loadRooms();
        }
    } else {
        showError('registerError', result.error);
    }
}

function handleLogout() {
    if (appState.ws) { appState.ws.close(); appState.ws = null; }
    appState.currentUser = null;
    appState.currentRoom = null;
    localStorage.removeItem('bingopoker_user');
    history.pushState({}, '', '/');
    showScreen('roomSelectScreen');
    showLoginModal();
}

function updateGameUserDisplay() {
    const el = document.getElementById('gameUserDisplay');
    if (!el || !appState.currentUser) return;
    const color = appState.currentUser.sessionColor;
    const dot = color ? `<span style="background:${color};width:12px;height:12px;border-radius:50%;display:inline-block;margin-right:6px;"></span>` : '';
    el.innerHTML = dot + escapeHtml(appState.currentUser.username);
}

function updateUserDisplay() {
    if (!appState.currentUser) return;
    
    const display = document.getElementById('currentUserDisplay');
    if (display) {
        display.textContent = appState.currentUser.username;
    }
    
    const roleBtn = document.getElementById('roleSwapBtn');
    if (roleBtn && appState.currentUser.role) {
        roleBtn.textContent = appState.currentUser.role.charAt(0).toUpperCase() + appState.currentUser.role.slice(1);
    }
}

async function handleRoleSwap() {
    if (!appState.currentUser) return;
    
    const newRole = appState.currentUser.role === 'worker' ? 'observer' : 'worker';
    appState.currentUser.role = newRole;
    
    const result = await BingoPokerAPI.updateRole(appState.currentUser.email, newRole);
    if (!result.success) {
        console.error('Failed to update role:', result.error);
        appState.currentUser.role = newRole === 'worker' ? 'observer' : 'worker';
        return;
    }
    
    localStorage.setItem('bingopoker_user', JSON.stringify(appState.currentUser));
    updateUserDisplay();
}

// ===== Room Selection =====

async function loadRooms() {
    showLoading(true);
    const result = await BingoPokerAPI.listRooms();
    showLoading(false);
    
    const roomsList = document.getElementById('roomsList');
    if (!roomsList) return;
    
    if (result.success) {
        appState.rooms = result.data.rooms || [];
        
        if (appState.rooms.length === 0) {
            roomsList.innerHTML = '<div class="loading">No active rooms. Create one to get started!</div>';
        } else {
            roomsList.innerHTML = appState.rooms.map(room => {
                const shareUrl = `${location.origin}/?r=${room.room_id}`;
                const isCreator = appState.currentUser && appState.currentUser.user_id === room.created_by;
                const deleteButton = isCreator ? `
                    <button class="btn btn-small btn-danger room-card-delete" onclick="handleDeleteRoom('${room.room_id}')">
                        Remove
                    </button>
                ` : '';
                return `
                <div class="room-card">
                    <h3>${escapeHtml(room.name)}</h3>
                    <div class="room-card-info">
                        <div>${room.user_count} participant${room.user_count !== 1 ? 's' : ''}</div>
                        <div><span class="room-link" onclick="copyRoomLink('${shareUrl}', this)" title="Click to copy invite link">${displayUrl(shareUrl)}</span></div>
                    </div>
                    <div class="room-card-buttons">
                        <button class="btn btn-primary btn-small room-card-button" onclick="joinRoom('${room.room_id}')">
                            Join
                        </button>
                        ${deleteButton}
                    </div>
                </div>`;
            }).join('');
        }
    } else {
        roomsList.innerHTML = '<div class="loading">Error loading rooms</div>';
    }
}

async function handleDeleteRoom(roomId) {
    const room = appState.rooms.find(r => r.room_id === roomId);
    const roomName = room ? room.name : roomId;
    const confirmed = confirm(`Are you sure you want to delete "${roomName}"? This cannot be undone.`);
    if (!confirmed) return;
    
    showLoading(true);
    const result = await BingoPokerAPI.deleteRoom(roomId, appState.currentUser.email);
    showLoading(false);
    
    if (result.success) {
        // Reload rooms list
        await loadRooms();
    } else {
        alert('Failed to delete room: ' + result.error);
    }
}

async function handleCreateRoom(e) {
    e.preventDefault();
    
    const roomName = document.getElementById('roomNameInput').value.trim();
    if (!roomName) {
        showError('createRoomError', 'Room name is required');
        return;
    }
    
    // Get grid - use default or custom
    let grid = GridUtils.DEFAULT_GRID;
    const gridInputSection = document.getElementById('gridInputSection');
    const customGridInputs = document.querySelectorAll('.grid-editor-cell input');
    
    // Only use custom grid if the section is visible and has inputs
    if (gridInputSection && !gridInputSection.classList.contains('hidden') && customGridInputs.length > 0) {
        grid = extractGridFromInputs(customGridInputs);
    }
    
    showLoading(true);
    const result = await BingoPokerAPI.createRoom(
        roomName,
        grid,
        appState.currentUser.email
    );
    showLoading(false);
    
    if (result.success) {
        const roomId = result.data.room_id;
        document.getElementById('createRoomForm').reset();
        hideError('createRoomError');
        loadRooms();
        await joinRoom(roomId);
    } else {
        showError('createRoomError', result.error);
    }
}

async function joinRoom(roomId) {
    showLoading(true);
    const result = await BingoPokerAPI.getRoom(roomId);
    showLoading(false);

    if (!result.success) {
        alert('Failed to join room: ' + result.error);
        return;
    }

    appState.currentRoom = { room_id: roomId, ...result.data.room };
    appState.currentGrid = appState.currentRoom.config.config.grid;
    appState.selectedBingoCells.clear();
    appState.selectedPokerValue = null;

    renderGameScreen();
    showScreen('gameScreen');
    history.pushState({ room: roomId }, '', `?r=${roomId}`);
    connectWebSocket(roomId);
}

async function handleLeaveRoom() {
    if (appState.ws) {
        appState.ws.close();
        appState.ws = null;
    }
    appState.currentRoom = null;
    appState.selectedBingoCells.clear();
    appState.selectedPokerValue = null;
    history.pushState({}, '', '/');
    showScreen('roomSelectScreen');
    loadRooms();
}

function handleDownloadGrid() {
    if (!appState.currentGrid || !appState.currentRoom) return;
    
    const config = {
        name: `${appState.currentRoom.config.name} - Bingo Config`,
        grid: appState.currentGrid
    };
    
    const json = JSON.stringify(config, null, 2);
    const blob = new Blob([json], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `bingo-config-${appState.currentRoom.room_id}.json`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
}

// ===== Game Screen Rendering =====

function renderGameScreen() {
    if (!appState.currentRoom) return;

    renderBingoGrid();
    renderPokerValues();
    renderUsers();
    renderRoundControls();

    const roomTitle = document.getElementById('roomTitle');
    if (roomTitle) roomTitle.textContent = appState.currentRoom.config.name;

    const roomIdDisplay = document.getElementById('roomIdDisplay');
    if (roomIdDisplay) {
        const shareUrl = `${location.origin}/?r=${appState.currentRoom.room_id}`;
        roomIdDisplay.innerHTML = `<span class="room-link" onclick="copyRoomLink('${shareUrl}', this)" title="Click to copy invite link">${displayUrl(shareUrl)}</span>`;
    }
}

function copyRoomLink(url, el) {
    navigator.clipboard.writeText(url).then(() => {
        const orig = el.textContent;
        el.textContent = 'Copied!';
        setTimeout(() => { el.textContent = orig; }, 1500);
    });
}

function displayUrl(url) {
    return url.replace(/^https?:\/\/(www\.)?/, '');
}

function renderBingoGrid() {
    const grid = document.getElementById('bingoGrid');
    if (!grid || !appState.currentGrid) return;

    const revealed = appState.currentRoom?.session?.revealed || false;
    const bingoSelections = appState.currentRoom?.session?.bingo_selections || {};
    const sessionUsers = appState.currentRoom?.session?.users || [];
    const myEmail = appState.currentUser?.email;

    // Build map of cellKey -> [user] filtered by visibility rules:
    // Observer selections always visible; worker selections only visible to self or after reveal
    const cellUsers = {};
    for (const user of sessionUsers) {
        const isObserver = user.role === 'observer';
        const isMe = user.email === myEmail;
        if (!isObserver && !isMe && !revealed) continue;
        const cells = bingoSelections[user.email] || [];
        for (const [r, c] of cells) {
            const key = `${r}-${c}`;
            if (!cellUsers[key]) cellUsers[key] = [];
            cellUsers[key].push(user);
        }
    }

    grid.innerHTML = '';

    for (let row = 0; row < 5; row++) {
        for (let col = 0; col < 5; col++) {
            const cell = appState.currentGrid[row][col];
            const isCenter = GridUtils.isCenterCell(row, col);
            const cellKey = `${row}-${col}`;
            const isMySelection = appState.selectedBingoCells.has(cellKey);
            const usersOnCell = cellUsers[cellKey] || [];

            const cellEl = document.createElement('div');
            cellEl.className = 'bingo-cell'
                + (isCenter ? ' center' : '')
                + (isMySelection ? ' selected' : '')
                + (revealed ? ' frozen' : '');
            cellEl.style.position = 'relative';

            const label = document.createElement('span');
            label.textContent = cell;
            cellEl.appendChild(label);

            // Render colored dots for each user who selected this cell
            if (usersOnCell.length > 0) {
                const dotsEl = document.createElement('div');
                dotsEl.className = 'cell-user-dots';
                for (const u of usersOnCell) {
                    const dot = document.createElement('span');
                    dot.className = 'cell-user-dot';
                    dot.style.backgroundColor = u.color;
                    dot.title = u.username;
                    dotsEl.appendChild(dot);
                }
                cellEl.appendChild(dotsEl);
            }

            if (!revealed) {
                cellEl.addEventListener('click', () => toggleBingoCell(row, col));
            }

            grid.appendChild(cellEl);
        }
    }
}

function toggleBingoCell(row, col) {
    const cellKey = `${row}-${col}`;
    if (appState.selectedBingoCells.has(cellKey)) {
        appState.selectedBingoCells.delete(cellKey);
    } else {
        appState.selectedBingoCells.add(cellKey);
    }
    wsSend('bingo_select', { row, col });
    renderBingoGrid();
}

function renderPokerValues() {
    const container = document.getElementById('pokerValues');    
    if (!container) return;

    const revealed = appState.currentRoom?.session?.revealed || false;
    const pokerValues = ['0', '1', '2', '3', '5', '8', '13', '21', 'split'];

    container.innerHTML = pokerValues.map(value => `
        <button class="poker-btn${appState.selectedPokerValue === value ? ' active' : ''}${revealed ? ' frozen' : ''}"
                ${revealed ? 'disabled' : `onclick="selectPokerValue('${value}')"`}>
            ${value}
        </button>
    `).join('');
}

function selectPokerValue(value) {
    appState.selectedPokerValue = value;
    wsSend('poker_select', { value });
    renderPokerValues();
}

function renderRoundControls() {
    const revealed = appState.currentRoom?.session?.revealed || false;
    const revealBtn = document.getElementById('revealBtn');
    const resetBtn = document.getElementById('resetBtn');
    if (!revealBtn || !resetBtn) return;

    revealBtn.disabled = revealed;
    revealBtn.style.opacity = revealed ? '0.4' : '1';
    revealBtn.style.cursor = revealed ? 'not-allowed' : 'pointer';

    resetBtn.disabled = !revealed;
    resetBtn.style.opacity = !revealed ? '0.4' : '1';
    resetBtn.style.cursor = !revealed ? 'not-allowed' : 'pointer';

    renderRevealedStatus(revealed);
}

function renderRevealedStatus(revealed) {
    const users = document.getElementById('usersList');
    if (!users) return;
    document.getElementById('revealSummary')?.remove();
    if (!revealed) return;

    const pokerSelections = appState.currentRoom?.session?.poker_selections || {};
    const numericValues = { '0': 0, '1': 1, '2': 2, '3': 3, '5': 5, '8': 8, '13': 13, '21': 21 };
    const values = Object.values(pokerSelections).filter(v => v in numericValues).map(v => numericValues[v]);
    const splitCount = Object.values(pokerSelections).filter(v => v === 'split').length;

    if (values.length > 0) {
        const avg = (values.reduce((a, b) => a + b, 0) / values.length).toFixed(1);
        const summary = document.createElement('div');
        summary.id = 'revealSummary';
        summary.style.cssText = 'margin-top:10px;padding:8px 10px;background:rgba(34,197,94,0.1);border-left:3px solid var(--success);border-radius:4px;font-size:12px;color:var(--text)';
        summary.innerHTML = `Avg: <strong>${avg}</strong>${splitCount ? ` &nbsp;·&nbsp; Split: <strong>${splitCount}</strong>` : ''}`;
        users.after(summary);
    }
}

function renderUsers() {
    const usersList = document.getElementById('usersList');
    const userCount = document.getElementById('userCount');
    
    if (!usersList || !appState.currentRoom) return;
    
    const users = appState.currentRoom.session?.users || [];
    const count = users.length;
    
    const revealed = appState.currentRoom?.session?.revealed || false;
    const pokerSelections = appState.currentRoom?.session?.poker_selections || {};

    if (userCount) userCount.textContent = count;

    usersList.innerHTML = users.map(user => {
        const hasSelection = !!pokerSelections[user.email];
        const pokerValue = revealed ? (pokerSelections[user.email] || '—') : (hasSelection ? '?' : '—');
        const statusText = revealed
            ? `<strong style="color:var(--primary)">${pokerValue}</strong>`
            : (hasSelection ? 'ready' : 'waiting');
        const roleBadge = user.role === 'observer'
            ? `<span class="role-badge">Observer</span>`
            : '';
        return `
        <div class="user-item">
            <div class="user-color" style="background-color: ${user.color}"></div>
            <div class="user-name">${escapeHtml(user.username)}${roleBadge}</div>
            <div class="user-status">${statusText}</div>
        </div>`;
    }).join('');
}

// ===== WebSocket =====

function connectWebSocket(roomId) {
    const proto = location.protocol === 'https:' ? 'wss' : 'ws';
    const url = `${proto}://${location.host}/ws/${roomId}/${encodeURIComponent(appState.currentUser.email)}`;

    const ws = new WebSocket(url);
    appState.ws = ws;

    ws.onmessage = (event) => {
        let msg;
        try {
            msg = JSON.parse(event.data);
        } catch (e) {
            console.error('WS JSON parse error', e);
            return;
        }
        handleWsMessage(msg);
    };

    ws.onclose = () => {
        appState.ws = null;
    };

    ws.onerror = (err) => {
        console.error('WS error', err);
    };
}

function wsSend(type, payload = {}) {
    if (appState.ws && appState.ws.readyState === WebSocket.OPEN) {
        appState.ws.send(JSON.stringify({ type, payload }));
    }
}

function handleWsMessage(msg) {
    switch (msg.type) {
        case 'room_state': {
            appState.currentRoom = { ...appState.currentRoom, ...msg.payload };
            appState.currentGrid = msg.payload.config?.config?.grid || appState.currentGrid;
            const me = msg.payload.session?.users?.find(u => u.email === appState.currentUser.email);
            if (me) appState.currentUser.sessionColor = me.color;
            renderGameScreen();
            updateGameUserDisplay();
            break;
        }

        case 'user_joined':
        case 'user_left':
            if (appState.currentRoom?.session) {
                appState.currentRoom.session.users = msg.payload.users;
            }
            renderUsers();
            break;

        case 'bingo_updated':
            if (appState.currentRoom?.session) {
                appState.currentRoom.session.bingo_selections = msg.payload.bingo_selections;
            }
            renderBingoGrid();
            break;

        case 'poker_updated':
            renderUsers();
            break;

        case 'revealed':
            appState.currentRoom.session = {
                ...appState.currentRoom.session,
                bingo_selections: msg.payload.bingo_selections,
                poker_selections: msg.payload.poker_selections,
                revealed: true,
            };
            renderGameScreen();
            break;

        case 'replaced':
            // Server closed this connection because user reconnected from another tab
            appState.ws = null;
            alert('You joined this room from another tab or window.');
            break;

        case 'round_reset':
            appState.selectedBingoCells.clear();
            appState.selectedPokerValue = null;
            if (appState.currentRoom.session) {
                appState.currentRoom.session.bingo_selections = {};
                appState.currentRoom.session.poker_selections = {};
                appState.currentRoom.session.revealed = false;
            }
            renderGameScreen();
            break;
    }
}

// ===== Game Actions =====

function handleReveal() {
    wsSend('reveal');
}

function handleReset() {
    wsSend('reset');
}

// ===== Grid Editor =====

function useDefaultTemplate() {
    const gridInputSection = document.getElementById('gridInputSection');
    if (gridInputSection) {
        gridInputSection.classList.add('hidden');
        // Clear the grid editor to prevent confusion
        const gridEditor = document.getElementById('gridEditor');
        if (gridEditor) {
            gridEditor.innerHTML = '';
        }
    }
}

function useEmptyTemplate() {
    document.getElementById('gridInputSection').classList.remove('hidden');
    renderGridEditor();
}

function importGridJSON() {
    document.getElementById('gridFileInput').click();
}

function handleGridFileImport(event) {
    const file = event.target.files[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (e) => {
        try {
            const data = JSON.parse(e.target.result);
            const grid = Array.isArray(data) ? data : data.grid;
            if (!GridUtils.isValidGrid(grid)) {
                showError('createRoomError', 'Invalid grid: must be a 5×5 array.');
                return;
            }
            document.getElementById('gridInputSection').classList.remove('hidden');
            renderGridEditor(grid);
        } catch {
            showError('createRoomError', 'Could not parse JSON file.');
        }
        event.target.value = '';
    };
    reader.readAsText(file);
}

function renderGridEditor(prefill = null) {
    const editor = document.getElementById('gridEditor');
    if (!editor) return;
    
    editor.innerHTML = '';
    const source = prefill || GridUtils.createEmptyGrid();
    
    for (let row = 0; row < 5; row++) {
        for (let col = 0; col < 5; col++) {
            const input = document.createElement('input');
            input.type = 'text';
            input.maxLength = '50';
            input.placeholder = `Cell ${row + 1}-${col + 1}`;
            input.value = source[row][col];
            input.dataset.row = row;
            input.dataset.col = col;
            
            const wrapper = document.createElement('div');
            wrapper.className = 'grid-editor-cell';
            wrapper.appendChild(input);
            editor.appendChild(wrapper);
        }
    }
}

function extractGridFromInputs(inputs) {
    const grid = GridUtils.createEmptyGrid();
    inputs.forEach(input => {
        const row = parseInt(input.dataset.row);
        const col = parseInt(input.dataset.col);
        grid[row][col] = input.value || `Cell ${row + 1}-${col + 1}`;
    });
    return grid;
}

// ===== Debug Helpers (dev only) =====

async function debugDeleteUsers() {
    const r = await fetch('/api/debug/users', { method: 'DELETE' });
    const d = await r.json();
    alert(d.message);
    localStorage.removeItem('bingopoker_user');
    location.reload();
}

async function debugDeleteRooms() {
    const r = await fetch('/api/debug/rooms', { method: 'DELETE' });
    const d = await r.json();
    alert(d.message);
}

// ===== Utilities =====

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    // textContent escaping leaves quotes intact, which is unsafe inside attributes
    return div.innerHTML.replace(/"/g, '&quot;').replace(/'/g, '&#39;');
}
