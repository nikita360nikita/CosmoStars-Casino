// User Inventory & Gifts Management
class InventoryManager {
    constructor() {
        this.container = document.getElementById('inventory-grid');
        this.emptyState = document.getElementById('inventory-empty');
        this.totalValueEl = document.getElementById('inventory-total-value');
        this.countEl = document.getElementById('inventory-count');
        this.badgeEl = document.getElementById('nav-gifts-badge');

        this.modalInspect = document.getElementById('modal-inspect-gift');
        this.inspectImg = document.getElementById('inspect-gift-img');
        this.inspectEmoji = document.getElementById('inspect-gift-emoji');
        this.inspectTitle = document.getElementById('inspect-gift-title');
        this.inspectSerial = document.getElementById('inspect-gift-serial');
        this.inspectRarity = document.getElementById('inspect-gift-rarity');
        this.inspectDesc = document.getElementById('inspect-gift-desc');
        this.inspectValue = document.getElementById('inspect-gift-value');
        this.btnSellInspect = document.getElementById('btn-inspect-sell');
        this.btnSellAll = document.getElementById('btn-inventory-sell-all');

        this.currentInspectedGift = null;
        this.gifts = [];

        this.bindEvents();
    }

    bindEvents() {
        if (this.btnSellInspect) {
            this.btnSellInspect.addEventListener('click', () => {
                if (this.currentInspectedGift) {
                    this.sellGift(this.currentInspectedGift.id, this.currentInspectedGift.gift_name, this.currentInspectedGift.stars_value);
                }
            });
        }
        if (this.btnSellAll) {
            this.btnSellAll.addEventListener('click', () => {
                this.sellAllGifts();
            });
        }
    }

    async sellAllGifts() {
        if (!this.gifts || this.gifts.length === 0) return;
        const total = this.gifts.reduce((sum, g) => sum + g.stars_value, 0);
        if (!confirm(`Продать все ${this.gifts.length} подарков за ${total} ⭐️?`)) return;

        try {
            const res = await window.apiCall('/api/user/gifts/sell_all', 'POST');
            if (res.success) {
                window.sound.playWin();
                window.updateUserBalance(res.new_balance);
                window.showToast(`✅ ${res.message}`);
                if (window.Telegram?.WebApp?.HapticFeedback) {
                    window.Telegram.WebApp.HapticFeedback.notificationOccurred('success');
                }
                await this.loadGifts();
            } else {
                window.showToast(res.error || "Ошибка массовой продажи");
            }
        } catch (e) {
            console.error("Sell all error:", e);
            window.showToast("Ошибка сети при продаже");
        }
    }

    async loadGifts() {
        try {
            const res = await window.apiCall('/api/user/gifts', 'GET');
            if (res.success) {
                this.gifts = res.gifts || [];
                this.updateUI(res.total_value || 0, res.count || 0);
            }
        } catch (e) {
            console.error("Failed to load inventory:", e);
        }
    }

    updateUI(totalValue, count) {
        if (this.totalValueEl) this.totalValueEl.textContent = `${totalValue} ⭐️`;
        if (this.countEl) this.countEl.textContent = `${count} шт.`;

        // Update navigation badge
        if (this.badgeEl) {
            if (count > 0) {
                this.badgeEl.textContent = count;
                this.badgeEl.style.display = 'flex';
            } else {
                this.badgeEl.style.display = 'none';
            }
        }

        if (!this.container) return;

        if (this.gifts.length === 0) {
            this.container.style.display = 'none';
            if (this.emptyState) this.emptyState.style.display = 'flex';
            return;
        }

        if (this.emptyState) this.emptyState.style.display = 'none';
        this.container.style.display = 'grid';
        this.container.innerHTML = '';

        this.gifts.forEach(gift => {
            const card = document.createElement('div');
            card.className = `inventory-card rarity-${gift.rarity}`;

            const giftTitle = gift.ru_name || gift.gift_name;
            const serialText = `#${gift.serial_number}`;
            const editionText = `из ${gift.total_edition.toLocaleString()}`;

            card.innerHTML = `
                <div class="card-edition-tag">${serialText}</div>
                <div class="card-rarity-badge rarity-pill-${gift.rarity}">${gift.rarity.toUpperCase()}</div>
                <div class="inventory-card-media">
                    <img src="${gift.thumbnail || ''}" alt="${giftTitle}" class="gift-real-img" onerror="this.style.display='none'; this.nextElementSibling.style.display='block';">
                    <div class="gift-emoji-fallback" style="${gift.thumbnail ? 'display:none;' : ''}">${gift.gift_icon}</div>
                </div>
                <div class="inventory-card-title">${giftTitle}</div>
                <div class="inventory-card-edition">${editionText}</div>
                <div class="inventory-card-price">⭐️ ${gift.stars_value}</div>
                <div class="inventory-card-actions">
                    <button class="btn-sell-card" data-id="${gift.id}">Продать</button>
                    <button class="btn-inspect-card" data-id="${gift.id}">3D</button>
                </div>
            `;

            // Sell button
            const btnSell = card.querySelector('.btn-sell-card');
            btnSell.addEventListener('click', (e) => {
                e.stopPropagation();
                window.sound.playClick();
                this.sellGift(gift.id, giftTitle, gift.stars_value);
            });

            // Inspect card
            card.addEventListener('click', () => {
                window.sound.playClick();
                this.openInspect(gift);
            });

            this.container.appendChild(card);
        });
    }

    openInspect(gift) {
        this.currentInspectedGift = gift;
        const giftTitle = gift.ru_name || gift.gift_name;

        if (this.inspectImg) {
            this.inspectImg.src = gift.thumbnail || '';
            this.inspectImg.style.display = gift.thumbnail ? 'block' : 'none';
        }
        if (this.inspectEmoji) {
            this.inspectEmoji.textContent = gift.gift_icon;
            this.inspectEmoji.style.display = gift.thumbnail ? 'none' : 'block';
        }

        if (this.inspectTitle) this.inspectTitle.textContent = giftTitle;
        if (this.inspectSerial) this.inspectSerial.textContent = `#${gift.serial_number} из ${gift.total_edition.toLocaleString()}`;
        if (this.inspectRarity) {
            this.inspectRarity.textContent = gift.rarity.toUpperCase();
            this.inspectRarity.className = `inspect-rarity-pill rarity-pill-${gift.rarity}`;
        }
        if (this.inspectDesc) this.inspectDesc.textContent = gift.description || 'Официальный коллекционный подарок Telegram.';
        if (this.inspectValue) this.inspectValue.textContent = `+${gift.stars_value} ⭐️`;

        if (this.btnSellInspect) {
            this.btnSellInspect.textContent = `ПРОДАТЬ ЗА ${gift.stars_value} ⭐️`;
        }

        if (this.modalInspect) {
            this.modalInspect.classList.add('active');
        }
    }

    async sellGift(giftId, giftName, starsValue) {
        if (!confirm(`Продать подарок "${giftName}" за ${starsValue} ⭐️?`)) {
            return;
        }

        try {
            const res = await window.apiCall('/api/user/gifts/sell', 'POST', { gift_id: giftId });
            if (res.success) {
                window.sound.playWin();
                window.updateUserBalance(res.new_balance);
                window.showToast(`✅ ${res.message}`);

                if (window.Telegram?.WebApp?.HapticFeedback) {
                    window.Telegram.WebApp.HapticFeedback.notificationOccurred('success');
                }

                if (this.modalInspect) {
                    this.modalInspect.classList.remove('active');
                }

                // Reload inventory
                await this.loadGifts();
            } else {
                window.showToast(res.error || "Не удалось продать подарок");
            }
        } catch (e) {
            console.error("Sell error:", e);
            window.showToast("Ошибка сети при продаже");
        }
    }
}

window.InventoryManager = InventoryManager;
