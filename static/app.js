const API_BASE = '/api/v1';
let guestPals = JSON.parse(localStorage.getItem('guestPals')) || [];
let authToken = localStorage.getItem('token') || null;
let palSpeciesDropdown;
let targetSpeciesDropdown;
let palPassivesDropdown;
let targetPassivesDropdown;

document.addEventListener('DOMContentLoaded', () => {
    updateAuthUI();
    initDropdowns();
    initAuthModal();
    if (authToken) {
        fetchInventory();
    } else {
        renderInventory(guestPals);
        updateDiscoveries();
    }
});

// Update Header/Auth UI Status Indicator
function updateAuthUI() {
    const authStatus = document.getElementById('auth-status');
    if (!authStatus) return;

    if (authToken) {
        authStatus.innerHTML = `
            <span class="text-emerald-400 font-semibold">● Logged In</span>
            <button onclick="logout()" class="text-xs text-slate-400 underline hover:text-rose-400">Logout</button>
        `;
        fetchCurrentUser();
    } else {
        authStatus.innerHTML = `
            <span class="text-slate-400">Guest Mode (Local Only)</span>
            <button onclick="openAuthModal('login')" class="text-xs text-amber-400 underline hover:text-amber-300">Login</button>
            <button onclick="openAuthModal('register')" class="text-xs text-amber-400 underline hover:text-amber-300">Sign Up</button>
        `;
    }
}

// Best-effort: show the logged-in username once resolved
async function fetchCurrentUser() {
    try {
        const res = await fetch(`${API_BASE}/auth/me`, {
            headers: { 'Authorization': `Bearer ${authToken}` }
        });
        if (!res.ok) return;
        const user = await res.json();
        const nameSpan = document.querySelector('#auth-status span.text-emerald-400');
        if (nameSpan) nameSpan.innerText = `● ${user.username}`;
    } catch (err) {
        console.error(err);
    }
}

function logout() {
    localStorage.removeItem('token');
    localStorage.removeItem('guestPals');
    authToken = null;
    guestPals = [];
    updateAuthUI();
    renderInventory(guestPals);
    updateDiscoveries();
}

// ---- Auth Modal (Login / Sign Up) ----
function initAuthModal() {
    const modal = document.getElementById('auth-modal');
    const closeBtn = document.getElementById('auth-modal-close');
    const tabLogin = document.getElementById('auth-tab-login');
    const tabRegister = document.getElementById('auth-tab-register');
    const loginForm = document.getElementById('login-form');
    const registerForm = document.getElementById('register-form');
    if (!modal || !loginForm || !registerForm) return;

    closeBtn.addEventListener('click', closeAuthModal);
    modal.addEventListener('click', (e) => { if (e.target === modal) closeAuthModal(); });
    tabLogin.addEventListener('click', () => switchAuthTab('login'));
    tabRegister.addEventListener('click', () => switchAuthTab('register'));

    loginForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const username = document.getElementById('login-username').value;
        const password = document.getElementById('login-password').value;
        const errorEl = document.getElementById('login-error');
        errorEl.classList.add('hidden');

        try {
            const body = new URLSearchParams();
            body.set('username', username);
            body.set('password', password);
            const res = await fetch(`${API_BASE}/auth/token`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
                body
            });
            const data = await res.json();
            if (!res.ok) throw new Error(data.detail || 'Login failed');

            authToken = data.access_token;
            localStorage.setItem('token', authToken);
            closeAuthModal();
            updateAuthUI();
            fetchInventory();
        } catch (err) {
            errorEl.innerText = err.message;
            errorEl.classList.remove('hidden');
        }
    });

    registerForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const username = document.getElementById('register-username').value;
        const password = document.getElementById('register-password').value;
        const errorEl = document.getElementById('register-error');
        errorEl.classList.add('hidden');

        try {
            const res = await fetch(`${API_BASE}/auth/register`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username, password })
            });
            const data = await res.json();
            if (!res.ok) throw new Error(data.message || data.detail || 'Registration failed');

            // Auto-login right after a successful sign up
            const tokenBody = new URLSearchParams();
            tokenBody.set('username', username);
            tokenBody.set('password', password);
            const tokenRes = await fetch(`${API_BASE}/auth/token`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
                body: tokenBody
            });
            const tokenData = await tokenRes.json();
            if (!tokenRes.ok) throw new Error('Account created — please log in.');

            authToken = tokenData.access_token;
            localStorage.setItem('token', authToken);
            closeAuthModal();
            updateAuthUI();
            fetchInventory();
        } catch (err) {
            errorEl.innerText = err.message;
            errorEl.classList.remove('hidden');
        }
    });
}

function openAuthModal(tab) {
    const modal = document.getElementById('auth-modal');
    if (!modal) return;
    modal.classList.remove('hidden');
    switchAuthTab(tab || 'login');
}

function closeAuthModal() {
    const modal = document.getElementById('auth-modal');
    if (!modal) return;
    modal.classList.add('hidden');
    document.getElementById('login-error').classList.add('hidden');
    document.getElementById('register-error').classList.add('hidden');
}

function switchAuthTab(tab) {
    const tabLogin = document.getElementById('auth-tab-login');
    const tabRegister = document.getElementById('auth-tab-register');
    const loginForm = document.getElementById('login-form');
    const registerForm = document.getElementById('register-form');

    const activeClasses = ['bg-amber-500', 'text-slate-900'];
    const inactiveClasses = ['bg-slate-800', 'text-slate-300'];

    if (tab === 'register') {
        loginForm.classList.add('hidden');
        registerForm.classList.remove('hidden');
        tabRegister.classList.add(...activeClasses);
        tabRegister.classList.remove(...inactiveClasses);
        tabLogin.classList.add(...inactiveClasses);
        tabLogin.classList.remove(...activeClasses);
    } else {
        registerForm.classList.add('hidden');
        loginForm.classList.remove('hidden');
        tabLogin.classList.add(...activeClasses);
        tabLogin.classList.remove(...inactiveClasses);
        tabRegister.classList.add(...inactiveClasses);
        tabRegister.classList.remove(...activeClasses);
    }
}

// Searchable Dropdown Engine
function createSearchableDropdown({ hiddenInputId, triggerId, triggerTextId, menuId, searchId, optionsContainerId, placeholder }) {
    let optionsList = [];

    const hiddenInput = document.getElementById(hiddenInputId);
    const trigger = document.getElementById(triggerId);
    const triggerText = document.getElementById(triggerTextId);
    const menu = document.getElementById(menuId);
    const searchInput = document.getElementById(searchId);
    const optionsContainer = document.getElementById(optionsContainerId);

    if (!hiddenInput || !trigger || !triggerText || !menu || !searchInput || !optionsContainer) {
        console.error(`[Dropdown Setup Error] Could not find elements for trigger: #${triggerId}`);
        return { setOptions: () => {}, reset: () => {}, getValue: () => '' };
    }

    menu.addEventListener('click', (e) => e.stopPropagation());

    trigger.addEventListener('click', (e) => {
        e.stopPropagation();
        const isCurrentlyHidden = menu.classList.contains('hidden');

        document.querySelectorAll('[id$="-menu"]').forEach(m => m.classList.add('hidden'));

        if (isCurrentlyHidden) {
            menu.classList.remove('hidden');
            searchInput.value = '';
            filterOptions('');
            setTimeout(() => searchInput.focus(), 50);
        }
    });

    searchInput.addEventListener('input', (e) => {
        filterOptions(e.target.value);
    });

    optionsContainer.addEventListener('click', (e) => {
        const item = e.target.closest('.dropdown-item');
        if (item && item.dataset.value) {
            e.stopPropagation();
            selectValue(item.dataset.value);
        }
    });

    function filterOptions(query) {
        const cleanQuery = query.toLowerCase().trim();
        const filtered = optionsList.filter(item => item.toLowerCase().includes(cleanQuery));

        if (filtered.length === 0) {
            optionsContainer.innerHTML = `<div class="p-2 text-xs text-slate-500 italic">No species found</div>`;
            return;
        }

        optionsContainer.innerHTML = filtered.map(item => `
            <div data-value="${item}" class="dropdown-item px-3 py-1.5 text-sm rounded-md text-slate-200 hover:bg-amber-500 hover:text-slate-900 cursor-pointer font-medium transition select-none">
                ${item}
            </div>
        `).join('');
    }

    function selectValue(val) {
        hiddenInput.value = val;
        if (val) {
            triggerText.innerText = val;
            triggerText.classList.remove('text-slate-400');
            triggerText.classList.add('text-amber-400', 'font-semibold');
        } else {
            triggerText.innerText = placeholder;
            triggerText.classList.remove('text-amber-400', 'font-semibold');
            triggerText.classList.add('text-slate-400');
        }
        menu.classList.add('hidden');
    }

    return {
        setOptions: (items) => {
            optionsList = items;
            filterOptions('');
        },
        reset: () => selectValue(''),
        getValue: () => hiddenInput.value
    };
}

// Searchable Multi-Select Dropdown Engine (used for Passives, up to maxItems)
function createMultiSelectDropdown({ hiddenInputId, triggerId, chipsContainerId, menuId, searchId, optionsContainerId, placeholder, maxItems = 4 }) {
    let optionsList = [];
    let selected = [];

    const hiddenInput = document.getElementById(hiddenInputId);
    const trigger = document.getElementById(triggerId);
    const chipsContainer = document.getElementById(chipsContainerId);
    const menu = document.getElementById(menuId);
    const searchInput = document.getElementById(searchId);
    const optionsContainer = document.getElementById(optionsContainerId);

    if (!hiddenInput || !trigger || !chipsContainer || !menu || !searchInput || !optionsContainer) {
        console.error(`[MultiSelect Setup Error] Could not find elements for trigger: #${triggerId}`);
        return { setOptions: () => {}, reset: () => {}, getValues: () => [] };
    }

    menu.addEventListener('click', (e) => e.stopPropagation());

    trigger.addEventListener('click', (e) => {
        e.stopPropagation();
        const isCurrentlyHidden = menu.classList.contains('hidden');

        document.querySelectorAll('[id$="-menu"]').forEach(m => m.classList.add('hidden'));

        if (isCurrentlyHidden) {
            menu.classList.remove('hidden');
            searchInput.value = '';
            filterOptions('');
            setTimeout(() => searchInput.focus(), 50);
        }
    });

    searchInput.addEventListener('input', (e) => filterOptions(e.target.value));

    optionsContainer.addEventListener('click', (e) => {
        const item = e.target.closest('.dropdown-item');
        if (item && item.dataset.value) {
            e.stopPropagation();
            toggleValue(item.dataset.value);
        }
    });

    chipsContainer.addEventListener('click', (e) => {
        const removeBtn = e.target.closest('[data-remove]');
        if (removeBtn) {
            e.stopPropagation();
            toggleValue(removeBtn.dataset.remove);
        }
    });

    function filterOptions(query) {
        const cleanQuery = query.toLowerCase().trim();
        const filtered = optionsList.filter(item => item.toLowerCase().includes(cleanQuery));

        if (filtered.length === 0) {
            optionsContainer.innerHTML = `<div class="p-2 text-xs text-slate-500 italic">No passives found</div>`;
            return;
        }

        optionsContainer.innerHTML = filtered.map(item => {
            const isSelected = selected.includes(item);
            const atLimit = !isSelected && selected.length >= maxItems;
            const stateClasses = isSelected
                ? 'bg-amber-500 text-slate-900'
                : atLimit
                    ? 'text-slate-600 cursor-not-allowed'
                    : 'text-slate-200 hover:bg-amber-500 hover:text-slate-900 cursor-pointer';
            return `
                <div data-value="${item}" class="dropdown-item px-3 py-1.5 text-sm rounded-md font-medium transition select-none flex items-center justify-between ${stateClasses}">
                    <span>${item}</span>
                    ${isSelected ? '<span>&#10003;</span>' : ''}
                </div>
            `;
        }).join('');
    }

    function toggleValue(val) {
        const idx = selected.indexOf(val);
        if (idx >= 0) {
            selected.splice(idx, 1);
        } else {
            if (selected.length >= maxItems) return;
            selected.push(val);
        }
        syncState();
        filterOptions(searchInput.value);
    }

    function syncState() {
        hiddenInput.value = JSON.stringify(selected);
        renderChips();
    }

    function renderChips() {
        if (selected.length === 0) {
            chipsContainer.innerHTML = `<span class="text-slate-400">${placeholder}</span>`;
            return;
        }
        const chips = selected.map(v => `
            <span class="inline-flex items-center gap-1 bg-amber-500 text-slate-900 text-xs font-semibold px-2 py-0.5 rounded-md">
                ${v}
                <button type="button" data-remove="${v}" class="hover:text-rose-700 leading-none">&times;</button>
            </span>
        `).join('');
        chipsContainer.innerHTML = `${chips}<span class="text-[10px] text-slate-500">${selected.length}/${maxItems}</span>`;
    }

    return {
        setOptions: (items) => {
            optionsList = items;
            filterOptions('');
        },
        reset: () => {
            selected = [];
            syncState();
        },
        getValues: () => [...selected]
    };
}

// Global Click Closes Open Dropdowns
document.addEventListener('click', () => {
    document.querySelectorAll('[id$="-menu"]').forEach(m => m.classList.add('hidden'));
});

// Initialize Species Dropdowns from API
async function initDropdowns() {
    palSpeciesDropdown = createSearchableDropdown({
        hiddenInputId: 'pal-species',
        triggerId: 'pal-species-trigger',
        triggerTextId: 'pal-species-text',
        menuId: 'pal-species-menu',
        searchId: 'pal-species-search',
        optionsContainerId: 'pal-species-options',
        placeholder: 'Select Pal...'
    });

    targetSpeciesDropdown = createSearchableDropdown({
        hiddenInputId: 'target-species',
        triggerId: 'target-species-trigger',
        triggerTextId: 'target-species-text',
        menuId: 'target-species-menu',
        searchId: 'target-species-search',
        optionsContainerId: 'target-species-options',
        placeholder: 'Select Target Child...'
    });

    palPassivesDropdown = createMultiSelectDropdown({
        hiddenInputId: 'pal-passives',
        triggerId: 'pal-passives-trigger',
        chipsContainerId: 'pal-passives-chips',
        menuId: 'pal-passives-menu',
        searchId: 'pal-passives-search',
        optionsContainerId: 'pal-passives-options',
        placeholder: 'Select Passives...',
        maxItems: 4
    });

    targetPassivesDropdown = createMultiSelectDropdown({
        hiddenInputId: 'target-passives',
        triggerId: 'target-passives-trigger',
        chipsContainerId: 'target-passives-chips',
        menuId: 'target-passives-menu',
        searchId: 'target-passives-search',
        optionsContainerId: 'target-passives-options',
        placeholder: 'Desired Passives...',
        maxItems: 4
    });

    try {
        const res = await fetch(`${API_BASE}/breeding/species`);
        if (res.ok) {
            const speciesList = await res.json();
            palSpeciesDropdown.setOptions(speciesList);
            targetSpeciesDropdown.setOptions(speciesList);
        }
    } catch (err) {
        console.error('Failed to load species list from backend:', err);
    }

    try {
        const res = await fetch(`${API_BASE}/breeding/passives`);
        if (res.ok) {
            const passivesList = (await res.json()).map(p => p.name);
            palPassivesDropdown.setOptions(passivesList);
            targetPassivesDropdown.setOptions(passivesList);
        }
    } catch (err) {
        console.error('Failed to load passives list from backend:', err);
    }
}

// Fetch Logged-In User Inventory
async function fetchInventory() {
    try {
        const res = await fetch(`${API_BASE}/pals/`, {
            headers: { 'Authorization': `Bearer ${authToken}` }
        });
        if (!res.ok) throw new Error('Failed to fetch inventory');
        const pals = await res.json();
        renderInventory(pals);
        updateDiscoveries();
    } catch (err) {
        console.error(err);
    }
}

// Render Pal Inventory Box
function renderInventory(pals) {
    const list = document.getElementById('inventory-list');
    if (!list) return;

    if (!pals || pals.length === 0) {
        list.innerHTML = `<p class="col-span-full text-slate-500 text-sm italic">No Pals added yet. Add your first Pal above!</p>`;
        return;
    }

    list.innerHTML = pals.map((pal, idx) => `
        <div class="bg-slate-950 border border-slate-800 rounded-xl p-4 flex justify-between items-start">
            <div>
                <div class="flex items-center gap-2">
                    <span class="font-bold text-slate-100">${pal.species_name}</span>
                    <span class="text-xs px-2 py-0.5 rounded ${pal.gender === 'Male' || pal.gender === 'MALE' ? 'bg-blue-950 text-blue-400 border border-blue-800' : 'bg-rose-950 text-rose-400 border border-rose-800'}">
                        ${pal.gender}
                    </span>
                </div>
                <div class="mt-2 flex flex-wrap gap-1">
                    ${(pal.passives || []).length > 0 
                        ? pal.passives.map(p => `<span class="bg-slate-800 text-amber-300 text-xs px-2 py-0.5 rounded-md border border-slate-700">${p}</span>`).join('')
                        : `<span class="text-xs text-slate-600 italic">No Passives</span>`}
                </div>
            </div>
            <button onclick="deletePalItem(${idx}, ${pal.id || 'null'})" class="text-slate-600 hover:text-rose-400 text-sm font-bold p-1">✕</button>
        </div>
    `).join('');
}

async function deletePalItem(index, palId) {
    if (!authToken) {
        guestPals.splice(index, 1);
        localStorage.setItem('guestPals', JSON.stringify(guestPals));
        renderInventory(guestPals);
        updateDiscoveries();
    } else if (palId) {
        try {
            const res = await fetch(`${API_BASE}/pals/${palId}`, {
                method: 'DELETE',
                headers: { 'Authorization': `Bearer ${authToken}` }
            });
            if (res.ok) fetchInventory();
        } catch (err) {
            console.error(err);
        }
    }
}

// Render Breeding Results Section
function renderBreedingResults(results) {
    const section = document.getElementById('results-section');
    const container = document.getElementById('breeding-results');
    if (!section || !container) return;

    if (!results || results.length === 0) {
        container.innerHTML = `<p class="text-slate-400 text-sm italic">No valid parent combinations found in your inventory for this target.</p>`;
    } else {
        container.innerHTML = results.map(item => `
            <div class="bg-slate-950 border border-slate-800 rounded-xl p-4 flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
                <div class="flex items-center gap-4">
                    <div class="text-sm">
                        <span class="text-blue-400 font-semibold">♂ ${item.male_parent.species_name}</span>
                        <div class="text-xs text-slate-400">${(item.male_parent.passives || []).join(', ') || 'No Passives'}</div>
                    </div>
                    <span class="text-slate-600 font-bold">+</span>
                    <div class="text-sm">
                        <span class="text-rose-400 font-semibold">♀ ${item.female_parent.species_name}</span>
                        <div class="text-xs text-slate-400">${(item.female_parent.passives || []).join(', ') || 'No Passives'}</div>
                    </div>
                </div>
                <div class="text-right">
                    <div class="text-lg font-bold text-emerald-400">${(item.success_rate * 100).toFixed(1)}% Success</div>
                    <div class="text-xs text-slate-500">Expected Eggs: ~${item.expected_attempts || 1}</div>
                </div>
            </div>
        `).join('');
    }

    section.classList.remove('hidden');
}

// Add Pal Form Handler
document.getElementById('add-pal-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const species_name = palSpeciesDropdown.getValue();
    
    if (!species_name) {
        alert('Please select a Pal species.');
        return;
    }

    const rawGender = document.getElementById('pal-gender').value;
    const gender = rawGender.toUpperCase();
    const passives = palPassivesDropdown.getValues();

    const newPal = { species_name, gender, passives };

    if (!authToken) {
        guestPals.push(newPal);
        localStorage.setItem('guestPals', JSON.stringify(guestPals));
        document.getElementById('add-pal-form').reset();
        palSpeciesDropdown.reset();
        palPassivesDropdown.reset();
        renderInventory(guestPals);
        updateDiscoveries();
    } else {
        try {
            const res = await fetch(`${API_BASE}/pals/`, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${authToken}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(newPal)
            });
            if (!res.ok) throw new Error((await res.json()).detail || 'Failed to add Pal');

            document.getElementById('add-pal-form').reset();
            palSpeciesDropdown.reset();
            palPassivesDropdown.reset();
            fetchInventory();
        } catch (err) {
            alert(err.message);
        }
    }
});

// Breed Finder Form Handler
document.getElementById('breed-finder-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const target_species = targetSpeciesDropdown.getValue();

    if (!target_species) {
        alert('Please select a target species.');
        return;
    }

    const desired_passives = targetPassivesDropdown.getValues();

    const payload = { target_species, desired_passives, require_clean: true };
    if (!authToken) payload.inventory_override = guestPals;

    const headers = { 'Content-Type': 'application/json' };
    if (authToken) headers['Authorization'] = `Bearer ${authToken}`;

    try {
        const res = await fetch(`${API_BASE}/breeding/find-pairs`, {
            method: 'POST',
            headers,
            body: JSON.stringify(payload)
        });
        if (!res.ok) throw new Error((await res.json()).detail || 'No breeding pairs found');
        const results = await res.json();
        renderBreedingResults(results);
    } catch (err) {
        alert(err.message);
    }
});

// Function to render the breedable list in HTML
function renderDiscoveries(discoveries) {
    const container = document.getElementById('breedable-pals-list');
    if (!container) return;

    const childSpecies = Object.keys(discoveries);

    if (childSpecies.length === 0) {
        container.innerHTML = `<p class="text-slate-400 text-sm italic">Add more male & female Pals to unlock breeding combinations.</p>`;
        return;
    }

    // Show species reachable directly from your box first, deeper generations after.
    const minGeneration = (pairs) => Math.min(...pairs.map(p => p.generation || 1));
    const sortedSpecies = [...childSpecies].sort((a, b) =>
        minGeneration(discoveries[a]) - minGeneration(discoveries[b]) || a.localeCompare(b)
    );

    let html = `<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">`;

    for (const species of sortedSpecies) {
        const pairs = discoveries[species];
        const gen = minGeneration(pairs);
        const genBadge = gen > 1
            ? `<span class="text-[10px] px-1.5 py-0.5 rounded bg-purple-950 text-purple-300 border border-purple-800">Gen ${gen}</span>`
            : `<span class="text-[10px] px-1.5 py-0.5 rounded bg-emerald-950 text-emerald-300 border border-emerald-800">Gen 1</span>`;

        html += `
            <div class="bg-slate-950 p-3 rounded-xl border border-slate-800">
                <div class="flex items-center gap-2">
                    <h4 class="font-bold text-amber-400 text-base">${species}</h4>
                    ${genBadge}
                </div>
                <p class="text-xs text-slate-500 mb-2">${pairs.length} possible parent pair(s)</p>
                <ul class="text-xs space-y-1 text-slate-300">
        `;

        pairs.slice(0, 5).forEach(pair => {
            const m = pair.male_parent;
            const f = pair.female_parent;
            const note = (m.is_intermediate || f.is_intermediate)
                ? ` <span class="text-slate-500 italic">(breed intermediates first)</span>`
                : '';
            html += `<li>♂️ <strong class="text-blue-400">${m.species_name || m.species}</strong> + ♀️ <strong class="text-rose-400">${f.species_name || f.species}</strong>${note}</li>`;
        });
        if (pairs.length > 5) {
            html += `<li class="text-slate-500 italic">+ ${pairs.length - 5} more...</li>`;
        }

        html += `</ul></div>`;
    }

    html += `</div>`;
    container.innerHTML = html;
}

// Discover Breedable Pals Handler
async function updateDiscoveries() {
    const breedableContainer = document.getElementById('breedable-pals-list');
    if (!breedableContainer) return;

    try {
        const payload = authToken ? {} : { inventory_override: guestPals };
        const headers = { 'Content-Type': 'application/json' };
        if (authToken) headers['Authorization'] = `Bearer ${authToken}`;

        const response = await fetch(`${API_BASE}/breeding/discover`, {
            method: 'POST',
            headers: headers,
            body: JSON.stringify(payload)
        });

        if (!response.ok) {
            const errDetail = await response.json().catch(() => ({}));
            console.error("Discovery Endpoint Error:", response.status, errDetail);
            return;
        }

        const discoveries = await response.json();
        renderDiscoveries(discoveries);
    } catch (err) {
        console.error("Error fetching breedable pals:", err);
    }
}