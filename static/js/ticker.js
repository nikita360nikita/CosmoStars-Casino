// Live Drops Ticker System
class LiveTicker {
    constructor() {
        this.track = document.getElementById('live-ticker-track');
        this.drops = [];
        this.init();
    }

    async init() {
        if (!this.track) return;
        await this.loadDrops();
        // Refresh feed every 20 seconds
        setInterval(() => this.loadDrops(), 20000);
    }

    async loadDrops() {
        try {
            const res = await window.apiCall('/api/live_feed', 'GET');
            if (res.success && res.drops) {
                this.drops = res.drops;
                this.render();
            }
        } catch (e) {
            console.error("Live ticker error:", e);
        }
    }

    render() {
        if (!this.track || this.drops.length === 0) return;
        this.track.innerHTML = '';

        // Double the array for seamless infinite scroll
        const items = [...this.drops, ...this.drops];
        items.forEach(d => {
            const el = document.createElement('div');
            el.className = `ticker-pill rarity-${d.rarity || 'common'}`;
            const userName = d.first_name || d.username || 'Игрок';
            const shortName = userName.length > 8 ? userName.slice(0, 7) + '…' : userName;
            const giftName = d.ru_name || d.gift_name;
            const serial = d.serial_number ? `#${d.serial_number}` : '';

            el.innerHTML = `
                <div class="ticker-pill-icon">
                    <img src="${d.thumbnail || ''}" alt="${giftName}" onerror="this.style.display='none'; this.nextElementSibling.style.display='inline';" class="ticker-img">
                    <span class="ticker-emoji" style="${d.thumbnail ? 'display:none;' : ''}">${d.gift_icon || '🎁'}</span>
                </div>
                <div class="ticker-pill-info">
                    <span class="ticker-pill-title">${giftName} <small>${serial}</small></span>
                    <span class="ticker-pill-user">${shortName} • <b class="gold">${d.stars_value} ⭐️</b></span>
                </div>
            `;
            this.track.appendChild(el);
        });
    }

    addDrop(drop) {
        this.drops.unshift(drop);
        if (this.drops.length > 20) this.drops.pop();
        this.render();
    }
}

window.LiveTicker = LiveTicker;
