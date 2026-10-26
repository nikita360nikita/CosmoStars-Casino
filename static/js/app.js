// Main App State & Controller
window.currentUser = null;
window.apiPost = (url, body) => window.apiCall(url, 'POST', body);
window.updateBalance = (bal) => window.updateUserBalance(bal);
window.soundManager = window.sound;
window.confettiManager = window.confetti;

// API helper with Telegram initData header
window.apiCall = async function(endpoint, method = 'GET', body = null) {
    const headers = {
        'Content-Type': 'application/json',
        'X-Init-Data': window.Telegram?.WebApp?.initData || ''
    };

    const options = { method, headers };
    if (body) {
        if (window.currentUser && !body.user_id) {
            body.user_id = window.currentUser.telegram_id;
        }
        options.body = JSON.stringify(body);
    }

    try {
        const res = await fetch(endpoint, options);
        let data = null;
        try {
            data = await res.json();
        } catch (jsonErr) {
            console.warn("apiCall failed to parse JSON response:", jsonErr);
            return { success: false, error: `Ответ сервера (${res.status})` };
        }
        return data;
    } catch (netErr) {
        console.error("apiCall network error:", netErr);
        throw netErr;
    }
};

window.showToast = function(msg) {
    const container = document.getElementById('toast-container');
    if (!container) return;
    const toast = document.createElement('div');
    toast.className = 'toast';
    toast.textContent = msg;
    container.appendChild(toast);
    setTimeout(() => {
        toast.remove();
    }, 2800);
};

window.updateUserBalance = function(newBalance) {
    if (window.currentUser) {
        window.currentUser.balance = newBalance;
    }
    const balEl = document.getElementById('user-balance-val');
    if (balEl) {
        balEl.textContent = Number(newBalance).toLocaleString();
    }
};

window.showWinModal = function(amount, subtitleHtml = '') {
    const modal = document.getElementById('modal-win');
    const amountEl = document.getElementById('win-modal-amount');
    const subEl = document.getElementById('win-modal-sub');

    if (amountEl) amountEl.textContent = `+${amount} ⭐️`;
    if (subEl) subEl.innerHTML = subtitleHtml;
    if (modal) modal.classList.add('active');

    if (window.confetti) {
        window.confetti.fire(2500, 50);
    }
};

window.showFloatingWin = function(containerOrEl, amount, multiplier = null) {
    const parent = containerOrEl || document.querySelector('.main-content') || document.body;
    const badge = document.createElement('div');
    badge.className = 'floating-win-badge';
    badge.innerHTML = `
        <span class="fw-icon">🎉</span>
        <span class="fw-stars">+${amount} ⭐️</span>
        ${multiplier ? `<span class="fw-mult">${Number(multiplier).toFixed(2)}x</span>` : ''}
    `;

    const computedPos = window.getComputedStyle(parent).position;
    if (computedPos === 'static') {
        parent.style.position = 'relative';
    }

    parent.appendChild(badge);

    setTimeout(() => {
        badge.classList.add('fade-out');
        setTimeout(() => badge.remove(), 400);
    }, 1900);
};

window.showDropModal = function(item, giftDbId) {
    const modal = document.getElementById('modal-drop-celebration');
    if (!modal) return;

    const imgEl = document.getElementById('drop-modal-img');
    const emojiEl = document.getElementById('drop-modal-emoji');
    const titleEl = document.getElementById('drop-modal-title');
    const serialEl = document.getElementById('drop-modal-serial');
    const rarityEl = document.getElementById('drop-modal-rarity');
    const valueEl = document.getElementById('drop-modal-value');
    const glowEl = document.getElementById('drop-popup-glow');
    const btnQuickSell = document.getElementById('btn-drop-quick-sell');

    const giftTitle = item.ru_name || item.name;

    if (imgEl) {
        imgEl.src = item.thumbnail || '';
        imgEl.style.display = item.thumbnail ? 'block' : 'none';
    }
    if (emojiEl) {
        emojiEl.textContent = item.icon || '🎁';
        emojiEl.style.display = item.thumbnail ? 'none' : 'block';
    }

    if (titleEl) titleEl.textContent = giftTitle;
    if (serialEl) serialEl.textContent = `#${item.serial_number} из ${item.total_edition.toLocaleString()}`;
    if (rarityEl) {
        rarityEl.textContent = item.rarity.toUpperCase();
        rarityEl.className = `drop-rarity-pill rarity-pill-${item.rarity}`;
    }
    if (valueEl) valueEl.textContent = `⭐️ ${item.stars} Stars`;

    // Set glow color based on rarity
    if (glowEl) {
        glowEl.className = `drop-popup-glow glow-${item.rarity}`;
    }

    // Configure Quick Sell button
    if (btnQuickSell) {
        btnQuickSell.textContent = `💰 ПРОДАТЬ ЗА ${item.stars} ⭐️`;
        btnQuickSell.onclick = async () => {
            window.sound.playClick();
            try {
                const res = await window.apiCall('/api/user/gifts/sell', 'POST', { gift_id: giftDbId });
                if (res.success) {
                    window.sound.playWin();
                    window.updateUserBalance(res.new_balance);
                    window.showToast(`✅ ${res.message}`);
                    modal.classList.remove('active');
                    if (window.inventoryManager) {
                        window.inventoryManager.loadGifts();
                    }
                } else {
                    window.showToast(res.error || "Ошибка продажи");
                }
            } catch (e) {
                console.error(e);
            }
        };
    }

    modal.classList.add('active');
};

document.addEventListener('DOMContentLoaded', () => {
    // 1. Initialize Telegram WebApp SDK if available
    const tg = window.Telegram?.WebApp;
    if (tg) {
        tg.ready();
        tg.expand();
        if (tg.enableClosingConfirmation) {
            tg.enableClosingConfirmation();
        }
        if (tg.setHeaderColor) {
            tg.setHeaderColor('#0d101d');
        }
    }

    // 2. Sound Toggle Button
    const btnSound = document.getElementById('btn-sound-toggle');
    if (btnSound) {
        btnSound.addEventListener('click', () => {
            const enabled = window.sound.toggle();
            btnSound.textContent = enabled ? '🔊' : '🔇';
        });
    }

    // 3. Modals handling
    const modalDeposit = document.getElementById('modal-deposit');
    const modalWithdraw = document.getElementById('modal-withdraw');
    const modalDrop = document.getElementById('modal-drop-celebration');
    const modalInspect = document.getElementById('modal-inspect-gift');
    const modalWin = document.getElementById('modal-win');

    document.querySelectorAll('.btn-open-deposit').forEach(btn => {
        btn.addEventListener('click', () => {
            window.sound.playClick();
            if (modalDeposit) modalDeposit.classList.add('active');
        });
    });

    document.querySelectorAll('.modal-close-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            window.sound.playClick();
            const modal = btn.closest('.modal-overlay');
            if (modal) modal.classList.remove('active');
            document.querySelectorAll('.modal-overlay').forEach(m => m.classList.remove('active'));
        });
    });

    document.querySelectorAll('.modal-overlay').forEach(m => {
        m.addEventListener('click', (e) => {
            if (e.target === m) m.classList.remove('active');
        });
    });

    // Deposit Pack Buttons (Telegram Stars)
    document.querySelectorAll('.deposit-pack-btn').forEach(btn => {
        btn.addEventListener('click', async () => {
            window.sound.playClick();
            const stars = parseInt(btn.dataset.stars) || 50;

            if (tg && tg.initData) {
                window.showToast("Создание инвойса Stars...");
                try {
                    const res = await window.apiCall('/api/deposit/create_invoice', 'POST', {
                        stars_amount: stars
                    });
                    if (res.success && res.invoice_link) {
                        tg.openInvoice(res.invoice_link, (status) => {
                            if (status === 'paid') {
                                window.sound.playWin();
                                if (window.confetti) window.confetti.fire(3000, 60);
                                window.showToast(`✅ Успешно зачислено: +${stars} ⭐️!`);
                                modalDeposit.classList.remove('active');
                                reloadUserData();
                            } else {
                                window.showToast("Оплата отменена");
                            }
                        });
                    } else {
                        window.showToast(res.error || "Ошибка создания счета");
                    }
                } catch (e) {
                    console.error(e);
                    window.showToast("Ошибка связи с Telegram");
                }
            } else {
                // In browser test mode: Add demo stars
                try {
                    const res = await window.apiCall('/api/demo/add_stars', 'POST', {
                        amount: stars
                    });
                    if (res.success) {
                        window.sound.playWin();
                        if (window.confetti) window.confetti.fire(2000, 40);
                        window.updateUserBalance(res.new_balance);
                        window.showToast(`⭐️ [Тест] Баланс пополнен на ${stars} Stars!`);
                        modalDeposit.classList.remove('active');
                    }
                } catch (e) {
                    console.error(e);
                }
            }
        });
    });

    // 3.5. Withdrawal Modal Handlers
    const btnOpenWithdraw = document.getElementById('btn-open-withdraw');

    async function loadWithdrawalHistory() {
        const listEl = document.getElementById('withdraw-history-list');
        if (!listEl) return;
        try {
            const res = await window.apiCall('/api/withdraw/history', 'GET');
            if (res.success && res.withdrawals && res.withdrawals.length > 0) {
                listEl.innerHTML = '';
                res.withdrawals.forEach(w => {
                    const item = document.createElement('div');
                    item.className = 'withdraw-item';
                    const isOk = w.status === 'completed';
                    const statusClass = isOk ? 'status-ok' : 'status-pending';
                    const statusText = isOk ? '✅ Выплачено' : '⏳ В обработке';
                    item.innerHTML = `
                        <div class="withdraw-item-left">
                            <span class="withdraw-item-amount">${w.amount} ⭐️</span>
                            <span class="withdraw-item-dest">${w.method}: ${w.address}</span>
                        </div>
                        <span class="withdraw-status-badge ${statusClass}">${statusText}</span>
                    `;
                    listEl.appendChild(item);
                });
            } else {
                listEl.innerHTML = '<div class="withdraw-empty-hint">Заявок пока нет</div>';
            }
        } catch (e) {
            console.error(e);
        }
    }

    if (btnOpenWithdraw && modalWithdraw) {
        btnOpenWithdraw.addEventListener('click', () => {
            window.sound.playClick();
            modalWithdraw.classList.add('active');
            loadWithdrawalHistory();
        });
    }

    document.querySelectorAll('.btn-withdraw-method').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.btn-withdraw-method').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
        });
    });

    const btnSubmitWithdraw = document.getElementById('btn-submit-withdraw');
    if (btnSubmitWithdraw) {
        btnSubmitWithdraw.addEventListener('click', async () => {
            const amountInput = document.getElementById('withdraw-amount-input');
            const addressInput = document.getElementById('withdraw-address-input');
            const activeMethodBtn = document.querySelector('.btn-withdraw-method.active');

            const amount = parseInt(amountInput.value) || 0;
            const address = addressInput.value.trim();
            const method = activeMethodBtn ? activeMethodBtn.dataset.method : 'Telegram Stars';

            if (amount < 100) {
                window.showToast("Минимальная сумма вывода — 100 ⭐️");
                return;
            }
            if (!address) {
                window.showToast("Укажите реквизиты для вывода");
                return;
            }

            btnSubmitWithdraw.disabled = true;
            btnSubmitWithdraw.textContent = "СОЗДАНИЕ ЗАЯВКИ...";

            try {
                const res = await window.apiCall('/api/withdraw', 'POST', { amount, address, method });
                if (res && res.success) {
                    window.sound.playWin();
                    if (res.new_balance !== undefined) {
                        window.updateUserBalance(res.new_balance);
                    }
                    window.showToast(`✅ ${res.message || "Заявка на вывод создана!"}`);
                    addressInput.value = '';
                    loadWithdrawalHistory();
                } else {
                    const errMsg = (res && res.error) ? res.error : "Ошибка вывода";
                    window.showToast(`❌ ${errMsg}`);
                }
            } catch (e) {
                console.error("Withdrawal error:", e);
                window.showToast("Ошибка сети при выводе. Попробуйте еще раз.");
            } finally {
                btnSubmitWithdraw.disabled = false;
                btnSubmitWithdraw.textContent = "СОЗДАТЬ ЗАЯВКУ НА ВЫВОД";
            }
        });
    }

    // 4. Tab Navigation
    const navItems = document.querySelectorAll('.nav-item');
    const tabViews = document.querySelectorAll('.tab-view');

    window.switchTab = function(tabId) {
        navItems.forEach(n => {
            if (n.dataset.tab === tabId) n.classList.add('active');
            else n.classList.remove('active');
        });
        tabViews.forEach(v => {
            if (v.id === `tab-${tabId}`) v.classList.add('active');
            else v.classList.remove('active');
        });

        if (tabId === 'inventory') {
            if (window.inventoryManager) window.inventoryManager.loadGifts();
        }
        if (tabId === 'info') {
            loadLeaderboard();
        }
    };

    navItems.forEach(n => {
        n.addEventListener('click', () => {
            window.sound.playClick();
            if (tg?.HapticFeedback) {
                tg.HapticFeedback.selectionChanged();
            }
            window.switchTab(n.dataset.tab);
        });
    });

    // 5. Load User Profile
    async function reloadUserData() {
        try {
            const res = await window.apiCall('/api/user', 'GET');
            if (res.success && res.user) {
                window.currentUser = res.user;
                const displayName = res.user.first_name || 'Игрок';
                const username = res.user.username ? `@${res.user.username}` : `#${res.user.telegram_id}`;

                const nameEl = document.getElementById('user-display-name');
                const tagEl = document.getElementById('user-display-tag');
                const avEl = document.getElementById('user-avatar-text');

                if (nameEl) nameEl.textContent = displayName;
                if (tagEl) tagEl.textContent = username;
                if (avEl) avEl.textContent = displayName.charAt(0).toUpperCase();

                window.updateUserBalance(res.user.balance);

                // Update inventory badge
                const badgeEl = document.getElementById('nav-gifts-badge');
                if (badgeEl && res.gifts_count > 0) {
                    badgeEl.textContent = res.gifts_count;
                    badgeEl.style.display = 'flex';
                }
            }
        } catch (e) {
            console.error("Could not load user data", e);
        }
    }

    // 6. Load Leaderboard
    async function loadLeaderboard() {
        try {
            const res = await window.apiCall('/api/leaderboard', 'GET');
            const listEl = document.getElementById('leaderboard-list-el');
            if (!listEl || !res.leaders) return;
            listEl.innerHTML = '';
            res.leaders.forEach((l, idx) => {
                const row = document.createElement('div');
                row.className = 'leader-row';
                const rankClass = idx === 0 ? 'rank-1' : (idx === 1 ? 'rank-2' : (idx === 2 ? 'rank-3' : ''));
                const medal = idx === 0 ? '🥇' : (idx === 1 ? '🥈' : (idx === 2 ? '🥉' : `${idx + 1}`));
                row.innerHTML = `
                    <div class="leader-left">
                        <span class="leader-rank ${rankClass}">${medal}</span>
                        <div class="leader-details">
                            <span class="leader-name">${l.first_name || l.username || 'Игрок'}</span>
                            <span class="leader-tag">${l.username ? `@${l.username}` : ''}</span>
                        </div>
                    </div>
                    <span class="leader-balance">${Number(l.balance).toLocaleString()} ⭐️</span>
                `;
                listEl.appendChild(row);
            });
        } catch (e) {
            console.error(e);
        }
    }

    // Initialize all components
    window.liveTicker = new window.LiveTicker();
    window.inventoryManager = new window.InventoryManager();
    window.casesGame = new window.CasesGame();
    window.crashGame = new window.CrashGame();
    window.coinflipGame = new window.CoinflipGame();
    window.upgraderGame = new window.UpgraderGame();

    // Start with user data & inventory
    reloadUserData();
    window.inventoryManager.loadGifts();
});
