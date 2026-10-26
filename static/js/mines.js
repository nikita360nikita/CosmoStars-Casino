// ============================================================
// MINES (МИНЫ 5x5) GAME ENGINE - RubUp Style
// ============================================================

(function () {
    let currentSession = null;
    let inGame = false;
    let betAmount = 10;
    let minesCount = 3;
    let revealedCount = 0;
    let currentMultiplier = 1.0;

    const gridEl = document.getElementById("mines-grid");
    const betInput = document.getElementById("mines-bet-input");
    const minesCountInput = document.getElementById("mines-count-input");
    const minesCountVal = document.getElementById("mines-count-display");
    const btnStart = document.getElementById("btn-mines-start");
    const btnCashout = document.getElementById("btn-mines-cashout");
    const multDisplay = document.getElementById("mines-multiplier-badge");
    const nextMultDisplay = document.getElementById("mines-next-multiplier");

    function init() {
        if (!gridEl) return;
        renderEmptyGrid();

        if (betInput) {
            betInput.addEventListener("input", (e) => {
                betAmount = Math.max(1, parseInt(e.target.value) || 1);
            });
        }

        if (minesCountInput) {
            minesCountInput.addEventListener("input", (e) => {
                minesCount = Math.max(1, Math.min(24, parseInt(e.target.value) || 3));
                if (minesCountVal) minesCountVal.textContent = minesCount;
            });
        }

        // Quick bet presets
        document.querySelectorAll(".btn-preset-mines").forEach(btn => {
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

        // Quick mines selector buttons
        document.querySelectorAll(".btn-mines-quick").forEach(btn => {
            btn.addEventListener("click", () => {
                document.querySelectorAll(".btn-mines-quick").forEach(b => b.classList.remove("active"));
                btn.classList.add("active");
                const count = parseInt(btn.getAttribute("data-count"));
                minesCount = count;
                if (minesCountInput) minesCountInput.value = count;
                if (minesCountVal) minesCountVal.textContent = count;
            });
        });

        if (btnStart) btnStart.addEventListener("click", handleStart);
        if (btnCashout) btnCashout.addEventListener("click", handleCashout);
    }

    function renderEmptyGrid() {
        gridEl.innerHTML = "";
        for (let i = 0; i < 25; i++) {
            const tile = document.createElement("div");
            tile.className = "mines-tile";
            tile.dataset.index = i;
            tile.innerHTML = `<div class="tile-inner"><span class="tile-icon">💎</span></div>`;
            tile.addEventListener("click", () => handleTileClick(i));
            gridEl.appendChild(tile);
        }
    }

    async function handleStart() {
        if (inGame) return;
        betAmount = Math.max(1, parseInt(betInput.value) || 1);
        
        try {
            btnStart.disabled = true;
            btnStart.textContent = "ЗАГРУЗКА...";
            const res = await window.apiPost("/api/games/mines/start", {
                bet_amount: betAmount,
                mines_count: minesCount
            });

            if (!res.success) {
                window.showToast(res.error || "Ошибка запуска игры", "error");
                btnStart.disabled = false;
                btnStart.textContent = "ИГРАТЬ 💣";
                return;
            }

            if (res.new_balance !== undefined) {
                window.updateBalance(res.new_balance);
            }

            currentSession = res.session_id;
            inGame = true;
            revealedCount = 0;
            currentMultiplier = 1.0;

            renderEmptyGrid();
            gridEl.classList.remove("disabled", "lost");

            btnStart.style.display = "none";
            btnCashout.style.display = "flex";
            btnCashout.disabled = true;
            btnCashout.innerHTML = `<span>ЗАБРАТЬ</span> <b>0 ⭐️</b>`;

            if (multDisplay) multDisplay.textContent = "1.00x";
            if (window.soundManager) window.soundManager.play("click");
            window.showToast(`Игра началась! Мин на поле: ${minesCount}`, "info");

        } catch (e) {
            window.showToast("Сетевая ошибка: " + e.message, "error");
            btnStart.disabled = false;
            btnStart.textContent = "ИГРАТЬ 💣";
        }
    }

    async function handleTileClick(tileIndex) {
        if (!inGame || !currentSession) return;
        const tile = gridEl.children[tileIndex];
        if (!tile || tile.classList.contains("revealed")) return;

        tile.classList.add("loading");

        try {
            const res = await window.apiPost("/api/games/mines/reveal", {
                session_id: currentSession,
                tile_index: tileIndex
            });

            tile.classList.remove("loading");

            if (!res.success) {
                window.showToast(res.error || "Ошибка хода", "error");
                return;
            }

            if (res.hit_mine) {
                // BOOM!
                handleLoss(res.tile_index, res.mine_positions);
            } else {
                // Gem / Diamond!
                handleSafeTile(tile, res);
            }

        } catch (e) {
            tile.classList.remove("loading");
            window.showToast("Сетевая ошибка", "error");
        }
    }

    function handleSafeTile(tile, res) {
        tile.classList.add("revealed", "safe");
        tile.innerHTML = `<div class="tile-inner"><span class="tile-gem">💎</span></div>`;
        revealedCount = res.revealed_count;
        currentMultiplier = res.multiplier;

        if (window.soundManager) window.soundManager.play("win");
        if (window.Telegram?.WebApp?.HapticFeedback) {
            window.Telegram.WebApp.HapticFeedback.impactOccurred("medium");
        }

        if (multDisplay) multDisplay.textContent = `${currentMultiplier.toFixed(2)}x`;
        btnCashout.disabled = false;
        btnCashout.innerHTML = `<span>ЗАБРАТЬ</span> <b>${res.win_amount} ⭐️</b> <span class="cashout-mult">${currentMultiplier.toFixed(2)}x</span>`;

        if (res.status === "won") {
            // Cleared all safe tiles!
            inGame = false;
            revealAllMines(res.mine_positions);
            if (res.new_balance !== undefined) window.updateBalance(res.new_balance);
            if (window.confettiManager) window.confettiManager.burst();
            window.showWinModal(res.win_amount, `ДЖЕКПОТ! Все безопасные ячейки открыты (${currentMultiplier}x)!`);
            resetControls();
        }
    }

    function handleLoss(hitIndex, minePositions) {
        inGame = false;
        gridEl.classList.add("lost");

        const hitTile = gridEl.children[hitIndex];
        if (hitTile) {
            hitTile.classList.add("revealed", "mine", "exploded");
            hitTile.innerHTML = `<div class="tile-inner"><span class="tile-bomb">💥</span></div>`;
        }

        revealAllMines(minePositions, hitIndex);

        if (window.soundManager) window.soundManager.play("lose");
        if (window.Telegram?.WebApp?.HapticFeedback) {
            window.Telegram.WebApp.HapticFeedback.notificationOccurred("error");
        }

        window.showToast("💥 Взрыв! Мина взорвана", "error");
        resetControls();
    }

    function revealAllMines(minePositions, hitIndex = -1) {
        if (!minePositions) return;
        minePositions.forEach(idx => {
            if (idx === hitIndex) return;
            const tile = gridEl.children[idx];
            if (tile && !tile.classList.contains("revealed")) {
                tile.classList.add("revealed", "mine", "dimmed");
                tile.innerHTML = `<div class="tile-inner"><span class="tile-bomb">💣</span></div>`;
            }
        });
    }

    async function handleCashout() {
        if (!inGame || !currentSession || revealedCount === 0) return;

        btnCashout.disabled = true;
        btnCashout.textContent = "ВЫВОД...";

        try {
            const res = await window.apiPost("/api/games/mines/cashout", {
                session_id: currentSession
            });

            if (!res.success) {
                window.showToast(res.error || "Ошибка вывода", "error");
                btnCashout.disabled = false;
                return;
            }

            inGame = false;
            if (res.new_balance !== undefined) {
                window.updateBalance(res.new_balance);
            }

            revealAllMines(res.mine_positions);
            if (window.soundManager) window.soundManager.play("win");
            if (window.confettiManager) window.confettiManager.burst();
            window.showWinModal(res.win_amount, `Успешный забор! Коэффициент: ${res.multiplier.toFixed(2)}x`);

            resetControls();

        } catch (e) {
            window.showToast("Сетевая ошибка: " + e.message, "error");
            btnCashout.disabled = false;
        }
    }

    function resetControls() {
        btnStart.style.display = "block";
        btnStart.disabled = false;
        btnStart.textContent = "ИГРАТЬ 💣";
        btnCashout.style.display = "none";
        currentSession = null;
    }

    window.addEventListener("DOMContentLoaded", init);
})();
