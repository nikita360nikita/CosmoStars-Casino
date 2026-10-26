class CasesGame {
    constructor() {
        this.casesGrid = document.getElementById('cases-grid-view');
        this.caseOpenerView = document.getElementById('case-opener-view');
        this.btnBack = document.getElementById('btn-back-to-cases');
        this.activeCaseTitle = document.getElementById('active-case-title');
        this.btnOpenCase = document.getElementById('btn-open-case-action');
        this.dropsContainer = document.getElementById('case-drops-preview');
        this.reelTrack = document.getElementById('case-reel-track');
        this.reelViewport = document.getElementById('case-reel-viewport');

        this.currentCase = null;
        this.isOpening = false;
        this.casesList = [];

        this.bindEvents();
        this.loadCases();
    }

    bindEvents() {
        if (this.btnBack) {
            this.btnBack.addEventListener('click', () => {
                window.sound.playClick();
                this.showGrid();
            });
        }

        if (this.btnOpenCase) {
            this.btnOpenCase.addEventListener('click', () => {
                this.openCurrentCase();
            });
        }
    }

    async loadCases() {
        try {
            const res = await window.apiCall('/api/cases', 'GET');
            if (res.success && res.cases) {
                this.casesList = res.cases;
                this.renderCasesGrid();
            }
        } catch (e) {
            console.error(e);
        }
    }

    renderCasesGrid() {
        if (!this.casesGrid) return;
        this.casesGrid.innerHTML = '';

        this.casesList.forEach(c => {
            const card = document.createElement('div');
            card.className = 'case-card';

            const topItem = c.items[c.items.length - 1];
            const badgeHtml = c.badge ? `<div class="case-badge" style="background: ${c.badge_color || '#ffb703'};">${c.badge}</div>` : '';

            card.innerHTML = `
                ${badgeHtml}
                <div class="case-card-glow" style="background: ${c.gradient || 'transparent'};"></div>
                <div class="case-icon-wrap">
                    <img src="${topItem.thumbnail || ''}" alt="${c.name}" class="case-top-img" onerror="this.style.display='none'; this.nextElementSibling.style.display='block';">
                    <span class="case-emoji-fallback" style="${topItem.thumbnail ? 'display:none;' : ''}">${topItem.icon}</span>
                </div>
                <div class="case-info">
                    <div class="case-name">${c.name}</div>
                    <div class="case-sub">${c.subtitle || 'Telegram Gifts'}</div>
                </div>
                <div class="case-price-tag">
                    <span class="star-sparkle">⭐️</span>
                    <span>${c.price} Stars</span>
                </div>
            `;

            card.addEventListener('click', () => {
                window.sound.playClick();
                this.selectCase(c);
            });
            this.casesGrid.appendChild(card);
        });
    }

    selectCase(caseData) {
        this.currentCase = caseData;
        this.casesGrid.style.display = 'none';
        this.caseOpenerView.style.display = 'flex';
        this.activeCaseTitle.textContent = caseData.name;
        this.btnOpenCase.textContent = `ОТКРЫТЬ ЗА ${caseData.price} ⭐️`;

        // Reset track position
        this.reelTrack.style.transition = 'none';
        this.reelTrack.style.transform = 'translateX(0px)';

        // Prepopulate reel track with sample items
        this.populateInitialReel(caseData.items);

        // Render drops preview list
        this.dropsContainer.innerHTML = '';
        caseData.items.forEach(it => {
            const dropCard = document.createElement('div');
            dropCard.className = `drop-card rarity-${it.rarity}`;
            dropCard.innerHTML = `
                <div class="drop-rarity-dot"></div>
                <div class="drop-icon-wrap">
                    <img src="${it.thumbnail || ''}" alt="${it.name}" class="drop-img" onerror="this.style.display='none'; this.nextElementSibling.style.display='block';">
                    <span class="drop-emoji" style="${it.thumbnail ? 'display:none;' : ''}">${it.icon}</span>
                </div>
                <div class="drop-name">${it.ru_name || it.name}</div>
                <div class="drop-value">⭐️ ${it.stars}</div>
            `;
            this.dropsContainer.appendChild(dropCard);
        });
    }

    populateInitialReel(items) {
        this.reelTrack.innerHTML = '';
        for (let i = 0; i < 45; i++) {
            const randomItem = items[Math.floor(Math.random() * items.length)];
            const card = this.createReelCard(randomItem);
            this.reelTrack.appendChild(card);
        }
    }

    createReelCard(item) {
        const div = document.createElement('div');
        div.className = `reel-item rarity-${item.rarity}`;
        const name = item.ru_name || item.name;
        const serial = item.serial_number ? `#${item.serial_number}` : '';

        div.innerHTML = `
            <div class="reel-item-rarity-bar"></div>
            <div class="item-icon-box">
                <img src="${item.thumbnail || ''}" alt="${name}" class="reel-img" onerror="this.style.display='none'; this.nextElementSibling.style.display='block';">
                <span class="reel-emoji" style="${item.thumbnail ? 'display:none;' : ''}">${item.icon}</span>
            </div>
            <div class="item-name">${name}</div>
            <div class="item-serial">${serial}</div>
            <div class="item-stars">⭐️ ${item.stars}</div>
        `;
        return div;
    }

    showGrid() {
        if (this.isOpening) return;
        this.casesGrid.style.display = 'grid';
        this.caseOpenerView.style.display = 'none';
        this.currentCase = null;
    }

    async openCurrentCase() {
        if (this.isOpening || !this.currentCase) return;

        if (window.currentUser && window.currentUser.balance < this.currentCase.price) {
            window.showToast("Недостаточно звёзд на открытие кейса! Пополните баланс ⭐️");
            const modalDeposit = document.getElementById('modal-deposit');
            if (modalDeposit) modalDeposit.classList.add('active');
            return;
        }

        this.isOpening = true;
        this.btnOpenCase.disabled = true;
        this.btnBack.disabled = true;

        if (window.Telegram?.WebApp?.HapticFeedback) {
            window.Telegram.WebApp.HapticFeedback.impactOccurred('heavy');
        }

        try {
            const res = await window.apiCall('/api/cases/open', 'POST', {
                case_id: this.currentCase.id
            });

            if (!res.success) {
                window.showToast(res.error || "Ошибка открытия");
                this.isOpening = false;
                this.btnOpenCase.disabled = false;
                this.btnBack.disabled = false;
                return;
            }

            // Immediately deduct local balance preview
            window.updateUserBalance(res.new_balance);

            // Populate reel with the server reel items
            this.reelTrack.innerHTML = '';
            res.reel_items.forEach(it => {
                this.reelTrack.appendChild(this.createReelCard(it));
            });

            // Calculate precise scroll offset
            const cardWidth = 110;
            const viewportWidth = this.reelViewport.getBoundingClientRect().width;
            const stopIndex = res.stop_index; // 38
            // Randomized shift inside the winning card for realism
            const randomShift = (Math.random() * 60) - 30;
            const targetOffset = (stopIndex * cardWidth) + (cardWidth / 2) - (viewportWidth / 2) + randomShift;

            // Reset position
            this.reelTrack.style.transition = 'none';
            this.reelTrack.style.transform = 'translateX(0px)';

            // Trigger reflow
            void this.reelTrack.offsetWidth;

            // Smooth cubic-bezier deceleration curve
            this.reelTrack.style.transition = 'transform 5.5s cubic-bezier(0.12, 0.92, 0.16, 1)';
            this.reelTrack.style.transform = `translateX(-${targetOffset}px)`;

            // Sound ticks while scrolling
            let tickCount = 0;
            const maxTicks = 32;
            const playTicks = () => {
                if (tickCount < maxTicks && this.isOpening) {
                    window.sound.playCaseTick();
                    if (window.Telegram?.WebApp?.HapticFeedback) {
                        window.Telegram.WebApp.HapticFeedback.selectionChanged();
                    }
                    tickCount++;
                    const delay = 55 + Math.pow(tickCount, 1.85) * 8;
                    setTimeout(playTicks, delay);
                }
            };
            playTicks();

            // When animation completes (5.6s)
            setTimeout(() => {
                this.isOpening = false;
                this.btnOpenCase.disabled = false;
                this.btnBack.disabled = false;

                // Play win sound & fanfare
                window.sound.playWin();

                // Fire celebration confetti!
                if (window.confetti) {
                    window.confetti.fire(3500, 85);
                }

                if (window.Telegram?.WebApp?.HapticFeedback) {
                    window.Telegram.WebApp.HapticFeedback.notificationOccurred('success');
                }

                const item = res.winning_item;
                const giftTitle = item.ru_name || item.name;

                // Update live ticker with won gift
                if (window.liveTicker) {
                    window.liveTicker.addDrop({
                        id: res.gift_db_id,
                        first_name: window.currentUser ? window.currentUser.first_name : 'Вы',
                        gift_name: item.name,
                        ru_name: giftTitle,
                        gift_icon: item.icon,
                        thumbnail: item.thumbnail,
                        rarity: item.rarity,
                        stars_value: item.stars,
                        serial_number: item.serial_number
                    });
                }

                // Refresh inventory tab if initialized
                if (window.inventoryManager) {
                    window.inventoryManager.loadGifts();
                }

                // Show rich drop celebration modal
                window.showDropModal(item, res.gift_db_id);

            }, 5650);

        } catch (e) {
            console.error(e);
            window.showToast("Ошибка соединения");
            this.isOpening = false;
            this.btnOpenCase.disabled = false;
            this.btnBack.disabled = false;
        }
    }
}

window.CasesGame = CasesGame;
