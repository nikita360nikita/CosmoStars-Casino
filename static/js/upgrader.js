class UpgraderGame {
    constructor() {
        this.svgWheel = document.getElementById('upgrader-svg-wheel');
        this.needle = document.getElementById('upgrader-needle');
        this.chanceText = document.getElementById('upgrader-chance-val');
        this.multBadge = document.getElementById('upgrader-mult-badge');
        this.actionBtn = document.getElementById('btn-upgrader-action');

        // Dual Slots
        this.slotSourceImg = document.getElementById('slot-source-img');
        this.slotSourceEmoji = document.getElementById('slot-source-emoji');
        this.slotSourceName = document.getElementById('slot-source-name');
        this.slotSourceVal = document.getElementById('slot-source-val');

        this.slotTargetImg = document.getElementById('slot-target-img');
        this.slotTargetEmoji = document.getElementById('slot-target-emoji');
        this.slotTargetName = document.getElementById('slot-target-name');
        this.slotTargetVal = document.getElementById('slot-target-val');

        // Sources & Targets Containers
        this.sourcesContainer = document.getElementById('upgrader-inventory-sources');
        this.targetsContainer = document.getElementById('upgrader-target-catalog');
        this.btnToggleStars = document.getElementById('btn-toggle-stars-source');
        this.starsBox = document.getElementById('upgrader-stars-box');
        this.starsInput = document.getElementById('upgrader-stars-input');

        this.sourceMode = 'inventory'; // 'inventory' or 'stars'
        this.selectedSource = null; // { id, name, stars, thumbnail, icon } or { type: 'stars', stars: 25 }
        this.selectedTarget = null; // target gift object
        this.allGifts = [];
        this.userGifts = [];

        this.isSpinning = false;
        this.currentNeedleAngle = 0;

        this.bindEvents();
        this.init();
    }

    async init() {
        await this.loadCatalog();
        await this.loadUserSources();
        this.calculateChance();
    }

    bindEvents() {
        if (this.btnToggleStars) {
            this.btnToggleStars.addEventListener('click', () => {
                window.sound.playClick();
                if (this.sourceMode === 'inventory') {
                    this.setSourceMode('stars');
                } else {
                    this.setSourceMode('inventory');
                }
            });
        }

        if (this.starsInput) {
            this.starsInput.addEventListener('input', () => {
                const val = parseInt(this.starsInput.value) || 10;
                this.selectedSource = { type: 'stars', name: `${val} Stars`, stars: val, icon: '⭐️' };
                this.updateSourceSlotUI();
                this.calculateChance();
            });
        }

        // Quick star presets
        document.querySelectorAll('.btn-preset-upg-stars').forEach(btn => {
            btn.addEventListener('click', () => {
                window.sound.playClick();
                const val = parseInt(btn.dataset.val) || 25;
                if (this.starsInput) this.starsInput.value = val;
                this.selectedSource = { type: 'stars', name: `${val} Stars`, stars: val, icon: '⭐️' };
                this.updateSourceSlotUI();
                this.calculateChance();
            });
        });

        if (this.actionBtn) {
            this.actionBtn.addEventListener('click', () => {
                this.upgrade();
            });
        }
    }

    setSourceMode(mode) {
        this.sourceMode = mode;
        if (mode === 'stars') {
            this.sourcesContainer.style.display = 'none';
            this.starsBox.style.display = 'block';
            this.btnToggleStars.textContent = '🎒 Выбрать из инвентаря';
            const val = parseInt(this.starsInput.value) || 25;
            this.selectedSource = { type: 'stars', name: `${val} Stars`, stars: val, icon: '⭐️' };
        } else {
            this.sourcesContainer.style.display = 'flex';
            this.starsBox.style.display = 'none';
            this.btnToggleStars.textContent = '⭐️ Ввести Stars';
            if (this.userGifts.length > 0) {
                this.selectSourceGift(this.userGifts[0]);
            } else {
                this.selectedSource = null;
            }
        }
        this.updateSourceSlotUI();
        this.calculateChance();
    }

    async loadCatalog() {
        try {
            const res = await window.apiCall('/api/cases', 'GET');
            if (res.success && res.all_gifts) {
                this.allGifts = res.all_gifts;
                this.renderTargets();
                // Default target: Plush Bear or Eternal Rose
                const defaultTarget = this.allGifts.find(g => g.id === 'tg_bear') || this.allGifts[3];
                if (defaultTarget) {
                    this.selectTargetGift(defaultTarget);
                }
            }
        } catch (e) {
            console.error("Load upgrader catalog error:", e);
        }
    }

    async loadUserSources() {
        try {
            const res = await window.apiCall('/api/user/gifts', 'GET');
            if (res.success) {
                this.userGifts = res.gifts || [];
                this.renderSources();
            }
        } catch (e) {
            console.error("Load user gifts error:", e);
        }
    }

    renderSources() {
        if (!this.sourcesContainer) return;
        this.sourcesContainer.innerHTML = '';

        if (this.userGifts.length === 0) {
            this.sourcesContainer.innerHTML = `
                <div class="upgrader-empty-hint">
                    <span>У вас пока нет подарков для улучшения.</span>
                    <small>Используйте Stars ⭐️ или откройте кейс!</small>
                </div>
            `;
            // Auto switch to stars
            this.setSourceMode('stars');
            return;
        }

        this.userGifts.forEach((g, idx) => {
            const card = document.createElement('div');
            card.className = `upg-item-chip rarity-${g.rarity}`;
            if (idx === 0 && !this.selectedSource) {
                card.classList.add('selected');
                this.selectSourceGift(g);
            }

            const title = g.ru_name || g.gift_name;
            card.innerHTML = `
                <div class="chip-media">
                    <img src="${g.thumbnail || ''}" alt="${title}" onerror="this.style.display='none'; this.nextElementSibling.style.display='inline';" class="chip-img">
                    <span class="chip-emoji" style="${g.thumbnail ? 'display:none;' : ''}">${g.gift_icon}</span>
                </div>
                <div class="chip-info">
                    <span class="chip-name">${title}</span>
                    <span class="chip-val">⭐️ ${g.stars_value}</span>
                </div>
            `;

            card.addEventListener('click', () => {
                window.sound.playClick();
                document.querySelectorAll('.upg-item-chip').forEach(c => c.classList.remove('selected'));
                card.classList.add('selected');
                this.selectSourceGift(g);
            });

            this.sourcesContainer.appendChild(card);
        });
    }

    renderTargets() {
        if (!this.targetsContainer) return;
        this.targetsContainer.innerHTML = '';

        // Filter gifts that can be targeted (cost >= 50 Stars)
        const targets = this.allGifts.filter(g => g.stars >= 50);
        targets.forEach(g => {
            const card = document.createElement('div');
            card.className = `upg-target-card rarity-${g.rarity}`;
            if (this.selectedTarget && this.selectedTarget.id === g.id) {
                card.classList.add('selected');
            }

            const title = g.ru_name || g.name;
            card.innerHTML = `
                <div class="target-card-img-wrap">
                    <img src="${g.thumbnail || ''}" alt="${title}" onerror="this.style.display='none'; this.nextElementSibling.style.display='inline';" class="target-img">
                    <span class="target-emoji" style="${g.thumbnail ? 'display:none;' : ''}">${g.icon}</span>
                </div>
                <span class="target-name">${title}</span>
                <span class="target-price">⭐️ ${g.stars}</span>
            `;

            card.addEventListener('click', () => {
                window.sound.playClick();
                document.querySelectorAll('.upg-target-card').forEach(c => c.classList.remove('selected'));
                card.classList.add('selected');
                this.selectTargetGift(g);
            });

            this.targetsContainer.appendChild(card);
        });
    }

    selectSourceGift(gift) {
        this.selectedSource = {
            id: gift.id,
            name: gift.ru_name || gift.gift_name,
            stars: gift.stars_value,
            thumbnail: gift.thumbnail,
            icon: gift.gift_icon,
            rarity: gift.rarity
        };
        this.updateSourceSlotUI();
        this.calculateChance();
    }

    selectTargetGift(gift) {
        this.selectedTarget = gift;
        this.updateTargetSlotUI();
        this.calculateChance();
    }

    updateSourceSlotUI() {
        if (!this.selectedSource) {
            this.slotSourceName.textContent = "Выберите подарок";
            this.slotSourceVal.textContent = "0 ⭐️";
            this.slotSourceImg.style.display = 'none';
            this.slotSourceEmoji.style.display = 'inline';
            return;
        }

        const title = this.selectedSource.name;
        this.slotSourceName.textContent = title;
        this.slotSourceVal.textContent = `${this.selectedSource.stars} ⭐️`;

        if (this.selectedSource.thumbnail) {
            this.slotSourceImg.src = this.selectedSource.thumbnail;
            this.slotSourceImg.style.display = 'block';
            this.slotSourceEmoji.style.display = 'none';
        } else {
            this.slotSourceEmoji.textContent = this.selectedSource.icon || '⭐️';
            this.slotSourceEmoji.style.display = 'inline';
            this.slotSourceImg.style.display = 'none';
        }
    }

    updateTargetSlotUI() {
        if (!this.selectedTarget) return;

        const title = this.selectedTarget.ru_name || this.selectedTarget.name;
        this.slotTargetName.textContent = title;
        this.slotTargetVal.textContent = `${this.selectedTarget.stars} ⭐️`;

        if (this.selectedTarget.thumbnail) {
            this.slotTargetImg.src = this.selectedTarget.thumbnail;
            this.slotTargetImg.style.display = 'block';
            this.slotTargetEmoji.style.display = 'none';
        } else {
            this.slotTargetEmoji.textContent = this.selectedTarget.icon || '🎁';
            this.slotTargetEmoji.style.display = 'inline';
            this.slotTargetImg.style.display = 'none';
        }
    }

    calculateChance() {
        if (!this.selectedSource || !this.selectedTarget) return;

        const sourceVal = this.selectedSource.stars;
        const targetVal = this.selectedTarget.stars;

        if (sourceVal >= targetVal) {
            this.chanceText.textContent = "100%";
            this.multBadge.textContent = "x1.00";
            this.actionBtn.disabled = true;
            this.actionBtn.textContent = "ЦЕЛЬ ДОЛЖНА БЫТЬ ДОРОЖЕ";
            this.setSectorAngle(360);
            return;
        }

        this.actionBtn.disabled = false;
        const mult = (targetVal / sourceVal).toFixed(2);
        this.multBadge.textContent = `x${mult}`;

        // Formula: (source / target) * 96%
        const chance = Math.min(95.0, Math.max(0.5, (sourceVal / targetVal) * 96.0));
        this.chanceText.textContent = `${chance.toFixed(1)}%`;
        this.actionBtn.textContent = `⚡ УЛУЧШИТЬ ДО ${this.selectedTarget.ru_name || this.selectedTarget.name}`;

        const sectorAngle = (chance / 100.0) * 360.0;
        this.setSectorAngle(sectorAngle);
    }

    setSectorAngle(angleDeg) {
        const radius = 80;
        const cx = 100;
        const cy = 100;
        const angleRad = (angleDeg / 360.0) * 2 * Math.PI;

        const x2 = cx + radius * Math.cos(angleRad);
        const y2 = cy + radius * Math.sin(angleRad);
        const largeArc = angleRad > Math.PI ? 1 : 0;

        let pathData = "";
        if (angleDeg >= 359.5) {
            pathData = `M ${cx - radius} ${cy} A ${radius} ${radius} 0 1 0 ${cx + radius} ${cy} A ${radius} ${radius} 0 1 0 ${cx - radius} ${cy}`;
        } else {
            pathData = `M ${cx} ${cy} L ${cx + radius} ${cy} A ${radius} ${radius} 0 ${largeArc} 1 ${x2} ${y2} Z`;
        }

        const sectorEl = document.getElementById('upgrader-win-sector');
        if (sectorEl) {
            sectorEl.setAttribute('d', pathData);
        }
    }

    async upgrade() {
        if (this.isSpinning) return;
        if (!this.selectedSource || !this.selectedTarget) {
            window.showToast("Выберите исходный и целевой подарок!");
            return;
        }

        const payload = {
            target_gift_id: this.selectedTarget.id
        };

        if (this.selectedSource.type === 'stars') {
            payload.source_stars = this.selectedSource.stars;
            if (window.currentUser && window.currentUser.balance < payload.source_stars) {
                window.showToast("Недостаточно Stars на балансе!");
                const modal = document.getElementById('modal-deposit');
                if (modal) modal.classList.add('active');
                return;
            }
        } else {
            payload.source_gift_id = this.selectedSource.id;
        }

        this.isSpinning = true;
        this.actionBtn.disabled = true;

        if (window.Telegram?.WebApp?.HapticFeedback) {
            window.Telegram.WebApp.HapticFeedback.impactOccurred('heavy');
        }

        try {
            const res = await window.apiCall('/api/games/upgrader', 'POST', payload);
            if (!res.success) {
                window.showToast(res.error || "Ошибка апгрейда");
                this.isSpinning = false;
                this.actionBtn.disabled = false;
                return;
            }

            // Immediately update balance if Stars were deducted
            if (res.new_balance !== undefined) {
                window.updateUserBalance(res.new_balance);
            }

            // Animate spinning needle to stop_angle
            const extraRotations = 1440; // 4 full spins
            this.currentNeedleAngle += extraRotations + (res.stop_angle - (this.currentNeedleAngle % 360));
            this.needle.style.transform = `translate(-50%, -100%) rotate(${this.currentNeedleAngle}deg)`;

            // Sound ticks while spinning
            let tickCount = 0;
            const tickInterval = setInterval(() => {
                window.sound.playCaseTick();
                if (window.Telegram?.WebApp?.HapticFeedback) {
                    window.Telegram.WebApp.HapticFeedback.selectionChanged();
                }
                tickCount++;
                if (tickCount > 20) clearInterval(tickInterval);
            }, 150);

            // Wait for deceleration animation (3.5s)
            setTimeout(async () => {
                this.isSpinning = false;
                this.actionBtn.disabled = false;

                if (res.is_win) {
                    window.sound.playWin();
                    if (window.confetti) window.confetti.fire(3500, 80);
                    if (window.Telegram?.WebApp?.HapticFeedback) {
                        window.Telegram.WebApp.HapticFeedback.notificationOccurred('success');
                    }

                    // Reload inventory
                    if (window.inventoryManager) {
                        await window.inventoryManager.loadGifts();
                    }
                    await this.loadUserSources();

                    // Show winning modal celebration!
                    window.showDropModal(res.winning_item, res.gift_db_id);
                } else {
                    window.sound.playLose();
                    if (window.Telegram?.WebApp?.HapticFeedback) {
                        window.Telegram.WebApp.HapticFeedback.notificationOccurred('error');
                    }
                    window.showToast("💥 Улучшение не удалось! Подарок сгорел.");
                    if (window.inventoryManager) {
                        await window.inventoryManager.loadGifts();
                    }
                    await this.loadUserSources();
                }
            }, 3650);

        } catch (e) {
            console.error(e);
            window.showToast("Ошибка соединения");
            this.isSpinning = false;
            this.actionBtn.disabled = false;
        }
    }
}

window.UpgraderGame = UpgraderGame;
