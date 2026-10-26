class CoinflipGame {
    constructor() {
        this.coinInner = document.getElementById('coin-inner');
        this.btnHeads = document.getElementById('btn-choice-heads');
        this.btnTails = document.getElementById('btn-choice-tails');
        this.actionBtn = document.getElementById('btn-coinflip-action');
        this.betInput = document.getElementById('coinflip-bet-input');
        this.winPreview = document.getElementById('coinflip-win-preview');
        this.selectedSide = 'heads';
        this.isFlipping = false;
        this.currentRotation = 0;

        this.bindEvents();
        this.updatePreview();
    }

    updatePreview() {
        if (!this.winPreview) return;
        const bet = parseInt(this.betInput.value) || 0;
        this.winPreview.textContent = `${(bet * 1.95).toFixed(1)} ⭐`;
    }

    bindEvents() {
        if (this.betInput) {
            this.betInput.addEventListener('input', () => this.updatePreview());
        }

        if (this.btnHeads && this.btnTails) {
            this.btnHeads.addEventListener('click', () => {
                window.sound.playClick();
                this.selectedSide = 'heads';
                this.btnHeads.classList.add('selected');
                this.btnTails.classList.remove('selected');
            });

            this.btnTails.addEventListener('click', () => {
                window.sound.playClick();
                this.selectedSide = 'tails';
                this.btnTails.classList.add('selected');
                this.btnHeads.classList.remove('selected');
            });
        }

        if (this.actionBtn) {
            this.actionBtn.addEventListener('click', () => {
                this.play();
            });
        }

        // Quick presets
        document.querySelectorAll('.btn-preset-coinflip').forEach(btn => {
            btn.addEventListener('click', () => {
                window.sound.playClick();
                const val = btn.dataset.val;
                let cur = parseInt(this.betInput.value) || 10;
                if (val === '2x') cur = cur * 2;
                else if (val === 'half') cur = Math.max(1, Math.floor(cur / 2));
                else if (val === 'max') cur = window.currentUser ? window.currentUser.balance : 100;
                else cur += parseInt(val);
                this.betInput.value = Math.max(1, cur);
                this.updatePreview();
            });
        });
    }

    async play() {
        if (this.isFlipping) return;

        const bet = parseInt(this.betInput.value) || 0;
        if (bet <= 0) {
            window.showToast("Введите сумму ставки!");
            return;
        }
        if (window.currentUser && window.currentUser.balance < bet) {
            window.showToast("Недостаточно звёзд на балансе!");
            return;
        }

        this.isFlipping = true;
        this.actionBtn.disabled = true;
        window.sound.playCoinFlip();

        if (window.Telegram?.WebApp?.HapticFeedback) {
            window.Telegram.WebApp.HapticFeedback.impactOccurred('heavy');
        }

        try {
            const res = await window.apiCall('/api/games/coinflip', 'POST', {
                bet_amount: bet,
                side: this.selectedSide
            });

            if (!res.success) {
                window.showToast(res.error || "Ошибка игры");
                this.isFlipping = false;
                this.actionBtn.disabled = false;
                return;
            }

            // Calculate target degrees for 3D flip
            // 5 full spins (1800 deg) + final side (0 for heads, 180 for tails)
            const baseSpins = 1800;
            const targetSideAngle = res.winning_side === 'heads' ? 0 : 180;
            this.currentRotation += baseSpins + (targetSideAngle - (this.currentRotation % 360));
            if (this.currentRotation % 360 !== targetSideAngle) {
                this.currentRotation += targetSideAngle;
            }

            this.coinInner.style.transform = `rotateY(${this.currentRotation}deg)`;

            // Wait for flip animation to finish (1.2s)
            setTimeout(() => {
                this.isFlipping = false;
                this.actionBtn.disabled = false;
                window.updateUserBalance(res.new_balance);

                if (res.is_win) {
                    window.sound.playWin();
                    if (window.confetti) window.confetti.fire(2000, 40);
                    if (window.Telegram?.WebApp?.HapticFeedback) {
                        window.Telegram.WebApp.HapticFeedback.notificationOccurred('success');
                    }
                    const coinCard = this.coinInner ? this.coinInner.closest('.card') : null;
                    window.showFloatingWin(coinCard, res.win_amount, 1.95);
                } else {
                    window.sound.playLose();
                    if (window.Telegram?.WebApp?.HapticFeedback) {
                        window.Telegram.WebApp.HapticFeedback.notificationOccurred('error');
                    }
                    window.showToast(`Выпал ${res.winning_side === 'heads' ? 'Орёл' : 'Решка'}. В другой раз повезёт!`);
                }
            }, 1250);

        } catch (e) {
            console.error(e);
            window.showToast("Ошибка соединения");
            this.isFlipping = false;
            this.actionBtn.disabled = false;
        }
    }
}

window.CoinflipGame = CoinflipGame;
