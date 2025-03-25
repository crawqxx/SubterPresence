// ==UserScript==
// @name         SubterPresence JS
// @namespace    http://subter.org/
// @version      1.1
// @description  integrates with subter's play button to send game info
// @match        https://www.subter.org/games/*
// @grant        GM_xmlhttpRequest
// ==/UserScript==

(function() {
    'use strict';

    const statusStyle = `
        font-size: 14px;
        text-align: center;
        margin-bottom: 10px;
        padding: 5px;
        border-radius: 4px;
        background-color: rgba(46, 46, 46, 0.7);
        color: white;
    `;

    function getGameInfo() {
        const title = document.querySelector('h1.m-0')?.textContent.trim();
        const gameId = document.querySelector('.gamelaunch-btn')?.dataset.placeid ||
                      window.location.pathname.match(/\/games\/(\d+)/)?.[1];
        return {
            game_title: title || "Unknown Game",
            game_id: gameId || "unknown"
        };
    }

    function sendToPresenceApp() {
        const gameInfo = getGameInfo();
        if (!gameInfo.game_id) {
            updateStatus("Could not detect game ID", "error");
            return;
        }

        updateStatus("Sending to Presence App...", "sending");

        GM_xmlhttpRequest({
            method: 'POST',
            url: 'http://localhost:4789/import_game',
            data: JSON.stringify(gameInfo),
            headers: {
                'Content-Type': 'application/json'
            },
            onload: function(response) {
                if (response.status === 200) {
                    updateStatus("Sent to Presence App!", "success");
                } else {
                    updateStatus("Presence App not running", "error");
                }
            },
            onerror: function() {
                updateStatus("Connection failed", "error");
            }
        });
    }

    function updateStatus(text, type) {
        let color = "white";
        if (type === "success") color = "#4CAF50";
        if (type === "error") color = "#F44336";
        if (type === "sending") color = "#FFC107";

        if (!window.presenceStatusElement) {
            window.presenceStatusElement = document.createElement('div');
            window.presenceStatusElement.style = statusStyle;
            const playButtonContainer = document.querySelector('.gamelaunch-btn')?.closest('.d-flex');
            if (playButtonContainer) {
                playButtonContainer.parentNode.insertBefore(window.presenceStatusElement, playButtonContainer);
            }
        }

        window.presenceStatusElement.textContent = text;
        window.presenceStatusElement.style.color = color;
    }

    function enhancePlayButton() {
        const playButton = document.querySelector('.gamelaunch-btn');
        if (!playButton) return;

        const originalOnClick = playButton.onclick;
        playButton.onclick = function(e) {
            sendToPresenceApp();
            if (originalOnClick) {
                originalOnClick.call(this, e);
            }
        };

        playButton.style.transition = 'all 0.3s';
        playButton.addEventListener('mouseover', () => {
            playButton.style.filter = 'brightness(1.1)';
        });
        playButton.addEventListener('mouseout', () => {
            playButton.style.filter = '';
        });
    }

    const interval = setInterval(() => {
        if (document.querySelector('.gamelaunch-btn')) {
            clearInterval(interval);
            enhancePlayButton();
            updateStatus("Click play to send to Presence App", "ready");
        }
    }, 500);
})();