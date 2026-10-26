// ============================================================
// STORM (ШТОРМ) LIGHTNING TOWER ENGINE - RubUp Style
// ============================================================

(function () {
    let currentSession = null;
    let inGame = false;
    let betAmount = 10;
    let currentLevel = 0;
    const multipliers = [1.25, 1.65, 2.30, 3.40, 5.20, 8.50, 15.00];

    const towerEl = document.getElementById("storm-tower");
    const betInput = document.getElementById("storm-bet-input");
    const btnStart = document.getElementById("btn-storm-start");
    const btnCashout = document.getElementById("btn-storm-cashout");
    const currentMultText = document.getElementById("storm-current-mult");

    function init() {
        if (!towerEl) return;
        renderTower();

        if (betInput) {
            betInput.addEventListener("input", (e) => {
                betAmount = Math.max(1, parseInt(e.target.value) || 1);
            });
        }

        // Quick presets
        document.querySelectorAll(".btn-preset-storm").forEach(btn => {
            btn.addEventListener("click", () => {
                const action = btn.getAttribute("data-val");
                let cur = parseInt(betInput.value) || 10;
                if (action === "half") cur = Math.max(1, Math.floor(cur / 2));
                else if (action === "2x") cur = cur * 2;
                else cur = cur + parseInt(action);
                betInput.value = cur;
                betAmount = cur;
            });
        });

        if (btnStart) btnStart.addEventListener("click", handleStart);
        if (btnCashout) btnCashout.addEventListener("click", handleCashout);
    }

    function renderTower() {
        towerEl.innerHTML = "";
        // Render from top (Level 7 / 15x) down to bottom (Level 1 / 1.25x)
        for (let lvl = multipliers.length - 1; lvl >= 0; lvl--) {
            const row = document.createElement("div");
            row.className = "storm-row";
            row.dataset.level = lvl;
            if (lvl === 0) row.classList.add("active-level");

            const multBadge = document.createElement("div");
            multBadge.className = "storm-mult-badge";
            multBadge.textContent = `${multipliers[lvl].toFixed(2)}x`;

            const cloudsWrap = document.createElement("div");
            cloudsWrap.className = "storm-clouds-wrap";

            for (let c = 0; c < 3; c++) {
                const cloud = document.createElement("button");
                cloud.className = "storm-cloud-btn";
                cloud.dataset.cloud = c;
                cloud.innerHTML = `<span class="cloud-icon">☁️</span>`;
                cloud.addEventListener("click", () => handleCloudClick(lvl, c));
                cloudsWrap.appendChild(cloud);
            }

            row.appendChild(multBadge);
            row.appendChild(cloudsWrap);
            towerEl.appendChild(row);
        }
    }

    async function handleStart() {
        if (inGame) return;
        betAmount = Math.max(1, parseInt(betInput.value) || 1);

        try {
            btnStart.disabled = true;
            btnStart.textContent = "ПОДЪЁМ В НЕБО...";

            const res = await window.apiPost("/api/games/storm/start", {
                bet_amount: betAmount
            });

            if (!res.success) {
                window.showToast(res.error || "Ошибка старта", "error");
                btnStart.disabled = false;
                btnStart.textContent = "В ИГРУ";
                return;
            }

            if (res.new_balance !== undefined) window.updateBalance(res.new_balance);

            currentSession = res.session_id;
            inGame = true;
            currentLevel = 0;

            renderTower();
            updateActiveRowVisual();

            btnStart.style.display = "none";
            btnCashout.style.display = "flex";
            btnCashout.disabled = true;
            btnCashout.innerHTML = `<span>ЗАБРАТЬ</span> <b>0 ⭐️</b>`;

            if (currentMultText) currentMultText.textContent = "1.00x";
            if (window.soundManager) window.soundManager.play("click");

        } catch (e) {
            window.showToast("Сетевая ошибка: " + e.message, "error");
            btnStart.disabled = false;
            btnStart.textContent = "В ИГРУ";
        }
    }

    async function handleCloudClick(level, cloudIdx) {
        if (!inGame || !currentSession || level !== currentLevel) return;

        const row = towerEl.querySelector(`.storm-row[data-level="${level}"]`);
        const cloudBtn = row.querySelectorAll(".storm-cloud-btn")[cloudIdx];
        if (!cloudBtn || cloudBtn.classList.contains("picked")) return;

        cloudBtn.classList.add("loading");

        try {
            const res = await window.apiPost("/api/games/storm/step", {
                session_id: currentSession,
                chosen_cloud: cloudIdx
            });

            cloudBtn.classList.remove("loading");

            if (!res.success) {
                window.showToast(res.error || "Ошибка шага", "error");
                return;
            }

            if (res.hit_lightning) {
                // Struck by lightning!
                handleLightningStrike(level, cloudIdx, cloudBtn);
            } else {
                // Safe step!
                handleSafeStep(level, cloudIdx, cloudBtn, res);
            }

        } catch (e) {
            cloudBtn.classList.remove("loading");
            window.showToast("Сетевая ошибка", "error");
        }
    }

    function handleSafeStep(level, cloudIdx, cloudBtn, res) {
        cloudBtn.classList.add("picked", "safe");
        cloudBtn.innerHTML = `<span class="cloud-icon sun">☀️</span>`;

        const row = towerEl.querySelector(`.storm-row[data-level="${level}"]`);
        if (row) row.classList.add("passed");

        currentLevel = level + 1;
        if (currentMultText) currentMultText.textContent = `${res.multiplier.toFixed(2)}x`;

        if (window.soundManager) window.soundManager.play("win");
        if (window.Telegram?.WebApp?.HapticFeedback) {
            window.Telegram.WebApp.HapticFeedback.impactOccurred("heavy");
        }

        btnCashout.disabled = false;
        btnCashout.innerHTML = `<span>ЗАБРАТЬ</span> <b>${res.win_amount} ⭐️</b> <span class="cashout-mult">${res.multiplier.toFixed(2)}x</span>`;

        if (res.status === "won" || res.is_top_reached) {
            // Conquered the storm!
            inGame = false;
            if (res.new_balance !== undefined) window.updateBalance(res.new_balance);
            if (window.soundManager) window.soundManager.play("win");
            if (window.confetti) window.confetti.fire(2500, 60);

            const stormCard = towerEl.closest('.card');
            window.showFloatingWin(stormCard, res.win_amount, res.multiplier);
            resetControls();
        } else {
            updateActiveRowVisual();
        }
    }

    function handleLightningStrike(level, cloudIdx, cloudBtn) {
        inGame = false;
        cloudBtn.classList.add("picked", "struck");
        cloudBtn.innerHTML = `<span class="cloud-icon lightning">⚡</span>`;

        const row = towerEl.querySelector(`.storm-row[data-level="${level}"]`);
        if (row) row.classList.add("failed");

        if (window.soundManager) window.soundManager.play("lose");
        if (window.Telegram?.WebApp?.HapticFeedback) {
            window.Telegram.WebApp.HapticFeedback.notificationOccurred("error");
        }

        // Screen shake
        towerEl.classList.add("storm-shake");
        setTimeout(() => towerEl.classList.remove("storm-shake"), 600);

        window.showToast("⚡ УДАР МОЛНИИ! Шторм поглотил ставку", "error");
        resetControls();
    }

    function updateActiveRowVisual() {
        towerEl.querySelectorAll(".storm-row").forEach(row => {
            const lvl = parseInt(row.dataset.level);
            row.classList.remove("active-level");
            if (lvl === currentLevel) {
                row.classList.add("active-level");
            }
        });
    }

    async function handleCashout() {
        if (!inGame || !currentSession || currentLevel === 0) return;

        btnCashout.disabled = true;
        btnCashout.textContent = "ВЫВОД...";

        try {
            const res = await window.apiPost("/api/games/storm/cashout", {
                session_id: currentSession
            });

            if (!res.success) {
                window.showToast(res.error || "Ошибка вывода", "error");
                btnCashout.disabled = false;
                return;
            }

            inGame = false;
            if (res.new_balance !== undefined) window.updateBalance(res.new_balance);

            if (window.soundManager) window.soundManager.play("win");
            if (window.confetti) window.confetti.fire(2000, 45);

            if (window.Telegram?.WebApp?.HapticFeedback) {
                window.Telegram.WebApp.HapticFeedback.notificationOccurred("success");
            }

            // Real casino UX: Floating victory chip directly over storm card
            const stormCard = towerEl.closest('.card');
            window.showFloatingWin(stormCard, res.win_amount, res.multiplier);

            resetControls();

        } catch (e) {
            console.error("Storm cashout error:", e);
            window.showToast("Сетевая ошибка: " + e.message, "error");
            btnCashout.disabled = false;
        }
    }

    function resetControls() {
        btnStart.style.display = "block";
        btnStart.disabled = false;
        btnStart.textContent = "В ИГРУ";
        btnCashout.style.display = "none";
        btnCashout.disabled = false;
        currentSession = null;
        inGame = false;
    }

    window.addEventListener("DOMContentLoaded", init);
})();
