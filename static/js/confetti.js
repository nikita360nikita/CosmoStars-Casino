// Ultra-lightweight, high-performance canvas confetti celebration engine
class ConfettiManager {
    constructor() {
        this.canvas = null;
        this.ctx = null;
        this.particles = [];
        this.animationFrame = null;
        this.colors = ['#ffb703', '#fb8500', '#00f2fe', '#7928ca', '#10b981', '#f43f5e', '#a855f7'];
        this.init();
    }

    init() {
        this.canvas = document.createElement('canvas');
        this.canvas.id = 'confetti-canvas';
        this.canvas.style.position = 'fixed';
        this.canvas.style.top = '0';
        this.canvas.style.left = '0';
        this.canvas.style.width = '100vw';
        this.canvas.style.height = '100vh';
        this.canvas.style.pointerEvents = 'none';
        this.canvas.style.zIndex = '9999';
        document.body.appendChild(this.canvas);
        this.ctx = this.canvas.getContext('2d');

        const resize = () => {
            this.canvas.width = window.innerWidth;
            this.canvas.height = window.innerHeight;
        };
        resize();
        window.addEventListener('resize', resize);
    }

    fire(durationMs = 2500, particleCount = 70) {
        if (!this.ctx) return;
        const w = this.canvas.width;
        const h = this.canvas.height;

        for (let i = 0; i < particleCount; i++) {
            this.particles.push({
                x: w / 2 + (Math.random() - 0.5) * 120,
                y: h * 0.45 + (Math.random() - 0.5) * 60,
                vx: (Math.random() - 0.5) * 12,
                vy: -Math.random() * 12 - 5,
                size: Math.random() * 8 + 4,
                color: this.colors[Math.floor(Math.random() * this.colors.length)],
                rotation: Math.random() * 360,
                rotSpeed: (Math.random() - 0.5) * 12,
                shape: Math.random() > 0.4 ? 'rect' : 'circle',
                life: 1.0,
                decay: 0.012 + Math.random() * 0.008
            });
        }

        if (!this.animationFrame) {
            this.loop();
        }
    }

    burst(particleCount = 60) {
        this.fire(2200, particleCount);
    }

    loop() {
        if (!this.ctx) return;
        this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);

        for (let i = this.particles.length - 1; i >= 0; i--) {
            const p = this.particles[i];
            p.x += p.vx;
            p.y += p.vy;
            p.vy += 0.35; // gravity
            p.rotation += p.rotSpeed;
            p.life -= p.decay;

            if (p.life <= 0 || p.y > this.canvas.height) {
                this.particles.splice(i, 1);
                continue;
            }

            this.ctx.save();
            this.ctx.translate(p.x, p.y);
            this.ctx.rotate((p.rotation * Math.PI) / 180);
            this.ctx.globalAlpha = p.life;
            this.ctx.fillStyle = p.color;

            if (p.shape === 'rect') {
                this.ctx.fillRect(-p.size / 2, -p.size / 2, p.size, p.size * 0.6);
            } else {
                this.ctx.beginPath();
                this.ctx.arc(0, 0, p.size / 2, 0, Math.PI * 2);
                this.ctx.fill();
            }
            this.ctx.restore();
        }

        if (this.particles.length > 0) {
            this.animationFrame = requestAnimationFrame(() => this.loop());
        } else {
            this.animationFrame = null;
        }
    }
}

window.confetti = new ConfettiManager();
