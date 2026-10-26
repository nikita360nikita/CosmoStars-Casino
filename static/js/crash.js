class CrashGame {
    constructor() {
        this.canvas = document.getElementById('crash-canvas');
        this.ctx = this.canvas ? this.canvas.getContext('2d') : null;
        this.multiplierEl = document.getElementById('crash-multiplier-text');
        this.statusSubEl = document.getElementById('crash-status-sub');
        this.actionBtn = document.getElementById('btn-crash-action');
        this.betInput = document.getElementById('crash-bet-input');

        this.state = 'idle'; // 'idle', 'countdown', 'flying', 'crashed', 'cashed_out'
        this.currentMultiplier = 1.00;
        this.crashPoint = 0;
        this.sessionId = null;
        this.animationId = null;
        this.flightStartTime = 0;

        this.stars = [];
        this.particles = [];
        this.explosionParticles = [];
        this.shakeTimer = 0;

        this.initCanvas();
        this.bindEvents();
    }

    initCanvas() {
        if (!this.canvas) return;
        const resize = () => {
            const rect = this.canvas.getBoundingClientRect();
            this.canvas.width = rect.width * window.devicePixelRatio;
            this.canvas.height = rect.height * window.devicePixelRatio;
            if (this.ctx) {
                this.ctx.scale(window.devicePixelRatio, window.devicePixelRatio);
            }
        };
        resize();
        window.addEventListener('resize', resize);

        // Generate stars with various depths for parallax
        this.stars = [];
        for (let i = 0; i < 70; i++) {
            this.stars.push({
                x: Math.random() * 450,
                y: Math.random() * 260,
                size: Math.random() * 2.2 + 0.6,
                speed: Math.random() * 1.5 + 0.5,
                alpha: Math.random() * 0.8 + 0.2
            });
        }
        this.drawScene(30, 190);
    }

    bindEvents() {
        if (this.actionBtn) {
            this.actionBtn.addEventListener('click', () => {
                window.sound.playClick();
                if (this.state === 'idle') {
                    this.startRound();
                } else if (this.state === 'flying') {
                    this.cashOut();
                }
            });
        }

        // Quick presets
        document.querySelectorAll('.btn-preset-crash').forEach(btn => {
            btn.addEventListener('click', () => {
                window.sound.playClick();
                const val = btn.dataset.val;
                let cur = parseInt(this.betInput.value) || 10;
                if (val === '2x') cur = cur * 2;
                else if (val === 'half') cur = Math.max(1, Math.floor(cur / 2));
                else if (val === 'max') cur = window.currentUser ? window.currentUser.balance : 100;
                else cur += parseInt(val);
                this.betInput.value = Math.max(1, cur);
            });
        });
    }

    async startRound() {
        const bet = parseInt(this.betInput.value) || 0;
        if (bet <= 0) {
            window.showToast("Введите сумму ставки!");
            return;
        }
        if (window.currentUser && window.currentUser.balance < bet) {
            window.showToast("Недостаточно звёзд на балансе!");
            const modal = document.getElementById('modal-deposit');
            if (modal) modal.classList.add('active');
            return;
        }

        this.actionBtn.disabled = true;
        this.statusSubEl.textContent = "ПОДГОТОВКА ДВИГАТЕЛЕЙ...";

        try {
            const res = await window.apiCall('/api/games/crash/start', 'POST', { bet_amount: bet });
            if (!res.success) {
                window.showToast(res.error || "Ошибка запуска");
                this.actionBtn.disabled = false;
                this.statusSubEl.textContent = "ГОТОВ К ВЗЛЁТУ";
                return;
            }

            this.sessionId = res.session_id;
            this.crashPoint = res.crash_point;
            window.updateUserBalance(res.new_balance);

            // Start countdown
            this.state = 'countdown';
            this.multiplierEl.classList.remove('crashed');
            this.multiplierEl.textContent = '1.00x';
            this.statusSubEl.textContent = "СТАРТ ЧЕРЕЗ 1 СЕК...";

            setTimeout(() => {
                this.launchFlight();
            }, 800);

        } catch (e) {
            console.error(e);
            window.showToast("Ошибка сети при старте");
            this.actionBtn.disabled = false;
        }
    }

    launchFlight() {
        this.state = 'flying';
        this.currentMultiplier = 1.00;
        this.flightStartTime = performance.now();
        this.particles = [];
        this.explosionParticles = [];

        this.statusSubEl.textContent = "РАКЕТА В ПОЛЁТЕ";
        this.statusSubEl.style.color = '';

        this.actionBtn.disabled = false;
        this.actionBtn.className = 'btn-action btn-cashout';
        this.updateActionButtonText();

        if (window.Telegram?.WebApp?.HapticFeedback) {
            window.Telegram.WebApp.HapticFeedback.impactOccurred('medium');
        }

        this.animateFlight();
    }

    updateActionButtonText() {
        if (this.state === 'flying') {
            const bet = parseInt(this.betInput.value) || 10;
            const winPreview = Math.floor(bet * this.currentMultiplier);
            this.actionBtn.textContent = `ЗАБРАТЬ ${winPreview} ⭐ (${this.currentMultiplier.toFixed(2)}x)`;
        }
    }

    animateFlight() {
        if (this.state !== 'flying') return;

        const now = performance.now();
        const elapsedSec = (now - this.flightStartTime) / 1000;

        // Exponential multiplier curve
        this.currentMultiplier = +(1.00 + 0.08 * Math.pow(elapsedSec, 1.4) + 0.06 * elapsedSec).toFixed(2);
        this.multiplierEl.textContent = `${this.currentMultiplier.toFixed(2)}x`;
        this.updateActionButtonText();

        // Check if rocket reached crash point!
        if (this.currentMultiplier >= this.crashPoint) {
            this.triggerAutoCrash(this.crashPoint);
            return;
        }

        // Calculate rocket position on canvas
        const w = this.canvas.width / window.devicePixelRatio;
        const h = this.canvas.height / window.devicePixelRatio;

        const progress = Math.min(1, elapsedSec / 14);
        const rocketX = 35 + progress * (w - 95);
        const rocketY = (h - 45) - Math.pow(progress, 0.72) * (h - 85);

        // Add rocket flame particles
        for (let i = 0; i < 4; i++) {
            this.particles.push({
                x: rocketX - 12,
                y: rocketY + 8,
                vx: -Math.random() * 4 - 2,
                vy: (Math.random() - 0.5) * 3,
                size: Math.random() * 4 + 2,
                life: 1.0,
                color: Math.random() > 0.4 ? '#ffb703' : '#ef4444'
            });
        }

        // Shift stars for forward motion effect
        this.stars.forEach(s => {
            s.x -= s.speed * (1 + elapsedSec * 0.3);
            if (s.x < 0) s.x = w;
        });

        this.drawScene(rocketX, rocketY);

        this.animationId = requestAnimationFrame(() => this.animateFlight());
    }

    drawScene(rocketX, rocketY) {
        if (!this.ctx) return;
        const w = this.canvas.width / window.devicePixelRatio;
        const h = this.canvas.height / window.devicePixelRatio;

        this.ctx.save();

        // Screen shake effect on explosion
        if (this.shakeTimer > 0) {
            const shakeMag = this.shakeTimer * 6;
            this.ctx.translate((Math.random() - 0.5) * shakeMag, (Math.random() - 0.5) * shakeMag);
            this.shakeTimer -= 0.06;
        }

        this.ctx.clearRect(0, 0, w, h);

        // Draw starfield
        this.ctx.fillStyle = '#fff';
        this.stars.forEach(s => {
            this.ctx.globalAlpha = s.alpha;
            this.ctx.beginPath();
            this.ctx.arc(s.x, s.y, s.size, 0, Math.PI * 2);
            this.ctx.fill();
        });
        this.ctx.globalAlpha = 1;

        // Draw trajectory curve
        if (this.state === 'flying' || this.state === 'cashed_out' || this.state === 'crashed') {
            this.ctx.beginPath();
            this.ctx.moveTo(35, h - 45);
            this.ctx.quadraticCurveTo(w * 0.35, h - 45, rocketX, rocketY);
            this.ctx.strokeStyle = this.state === 'crashed' ? '#ef4444' : '#10b981';
            this.ctx.lineWidth = 3.5;
            this.ctx.shadowColor = this.state === 'crashed' ? '#ef4444' : '#10b981';
            this.ctx.shadowBlur = 12;
            this.ctx.stroke();
            this.ctx.shadowBlur = 0;

            // Gradient glow under curve
            this.ctx.lineTo(rocketX, h - 25);
            this.ctx.lineTo(35, h - 25);
            const grad = this.ctx.createLinearGradient(0, rocketY, 0, h - 25);
            grad.addColorStop(0, this.state === 'crashed' ? 'rgba(239, 68, 68, 0.3)' : 'rgba(16, 185, 129, 0.3)');
            grad.addColorStop(1, 'rgba(0, 0, 0, 0)');
            this.ctx.fillStyle = grad;
            this.ctx.fill();
        }

        // Draw flame particles
        for (let i = this.particles.length - 1; i >= 0; i--) {
            const p = this.particles[i];
            p.x += p.vx;
            p.y += p.vy;
            p.life -= 0.035;
            if (p.life <= 0) {
                this.particles.splice(i, 1);
                continue;
            }
            this.ctx.fillStyle = p.color;
            this.ctx.globalAlpha = p.life;
            this.ctx.beginPath();
            this.ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2);
            this.ctx.fill();
        }
        this.ctx.globalAlpha = 1;

        // Draw explosion particles
        for (let i = this.explosionParticles.length - 1; i >= 0; i--) {
            const ep = this.explosionParticles[i];
            ep.x += ep.vx;
            ep.y += ep.vy;
            ep.life -= 0.025;
            if (ep.life <= 0) {
                this.explosionParticles.splice(i, 1);
                continue;
            }
            this.ctx.fillStyle = ep.color;
            this.ctx.globalAlpha = ep.life;
            this.ctx.beginPath();
            this.ctx.arc(ep.x, ep.y, ep.size, 0, Math.PI * 2);
            this.ctx.fill();
        }
        this.ctx.globalAlpha = 1;

        // Draw Rocket or Explosion
        if (this.state === 'crashed') {
            this.ctx.font = '36px sans-serif';
            this.ctx.textAlign = 'center';
            this.ctx.fillText('💥', rocketX, rocketY + 12);
        } else {
            this.ctx.save();
            this.ctx.translate(rocketX, rocketY);
            this.ctx.rotate(this.state === 'flying' ? -Math.PI / 4.8 : 0);
            this.ctx.font = '30px sans-serif';
            this.ctx.textAlign = 'center';
            this.ctx.shadowColor = '#00f2fe';
            this.ctx.shadowBlur = 10;
            this.ctx.fillText('🚀', 0, 10);
            this.ctx.restore();
        }

        this.ctx.restore();
    }

    async cashOut() {
        if (this.state !== 'flying') return;
        this.actionBtn.disabled = true;

        try {
            const res = await window.apiCall('/api/games/crash/cashout', 'POST', {
                session_id: this.sessionId,
                multiplier: this.currentMultiplier
            });

            cancelAnimationFrame(this.animationId);

            if (res.is_win) {
                this.state = 'cashed_out';
                window.updateUserBalance(res.new_balance);
                window.sound.playWin();
                if (window.confetti) window.confetti.fire(3000, 60);

                if (window.Telegram?.WebApp?.HapticFeedback) {
                    window.Telegram.WebApp.HapticFeedback.notificationOccurred('success');
                }

                this.statusSubEl.textContent = `ВЫИГРЫШ: +${res.win_amount} ⭐ (${res.final_multiplier}x)`;
                this.statusSubEl.style.color = '#10b981';

                window.showWinModal(res.win_amount, `🚀 Забрали на ${res.final_multiplier}x!`);
            } else {
                this.triggerCrashEffect(res.actual_crash || this.currentMultiplier);
            }
        } catch (e) {
            console.error(e);
            window.showToast("Ошибка при выводе");
        } finally {
            this.resetControls();
        }
    }

    triggerAutoCrash(crashMult) {
        cancelAnimationFrame(this.animationId);
        this.triggerCrashEffect(crashMult);

        // Notify server that crash occurred
        window.apiCall('/api/games/crash/cashout', 'POST', {
            session_id: this.sessionId,
            multiplier: 9999.0 // Will result in loss
        }).catch(() => {});

        this.resetControls();
    }

    triggerCrashEffect(crashMult) {
        this.state = 'crashed';
        window.sound.playExplosion();
        this.shakeTimer = 1.0;

        if (window.Telegram?.WebApp?.HapticFeedback) {
            window.Telegram.WebApp.HapticFeedback.notificationOccurred('error');
        }

        this.multiplierEl.classList.add('crashed');
        this.multiplierEl.textContent = `${crashMult.toFixed(2)}x`;
        this.statusSubEl.textContent = `ВЗРЫВ! РАКЕТА РАЗБИЛАСЬ`;
        this.statusSubEl.style.color = '#ef4444';

        const w = this.canvas.width / window.devicePixelRatio;
        const h = this.canvas.height / window.devicePixelRatio;
        const crashX = w * 0.72;
        const crashY = h * 0.38;

        // Generate explosion particles
        this.explosionParticles = [];
        for (let i = 0; i < 35; i++) {
            const angle = Math.random() * Math.PI * 2;
            const speed = Math.random() * 8 + 2;
            this.explosionParticles.push({
                x: crashX,
                y: crashY,
                vx: Math.cos(angle) * speed,
                vy: Math.sin(angle) * speed,
                size: Math.random() * 5 + 3,
                life: 1.0,
                color: ['#ef4444', '#f59e0b', '#fbbf24', '#ffffff'][Math.floor(Math.random() * 4)]
            });
        }

        // Animate explosion fading
        let frames = 0;
        const animateBlast = () => {
            if (frames < 30) {
                this.drawScene(crashX, crashY);
                frames++;
                requestAnimationFrame(animateBlast);
            }
        };
        animateBlast();
    }

    resetControls() {
        setTimeout(() => {
            this.state = 'idle';
            this.actionBtn.disabled = false;
            this.actionBtn.className = 'btn-action btn-green';
            this.actionBtn.textContent = 'ВЗЛЁТ (ПОСТАВИТЬ)';
            this.statusSubEl.style.color = '';
            this.statusSubEl.textContent = "ГОТОВ К ВЗЛЁТУ";
        }, 2000);
    }
}

window.CrashGame = CrashGame;
