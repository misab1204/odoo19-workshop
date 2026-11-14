(function () {
    'use strict';

    const WAVE_HEIGHTS = [7, 13, 18, 10, 20, 15, 8, 17, 21, 12, 9, 19, 14, 7, 16, 20, 11, 8, 15, 18, 10, 13, 7, 11];

    function formatSeconds(sec) {
        if (!isFinite(sec) || sec < 0) {
            return '0:00';
        }
        const total = Math.round(sec);
        const m = Math.floor(total / 60);
        const s = total % 60;
        return m + ':' + (s < 10 ? '0' : '') + s;
    }

    function escapeHtml(str) {
        const div = document.createElement('div');
        div.textContent = str == null ? '' : String(str);
        return div.innerHTML;
    }

    function initQueue() {
        const searchInput = document.getElementById('ac-order-search');
        const tabBtns = document.querySelectorAll('.ac-tab-btn[data-filter]');
        const railBtns = document.querySelectorAll('.ac-rail-btn[data-rail-filter]');
        const rows = document.querySelectorAll('.ac-order-row');
        if (!searchInput && !tabBtns.length) {
            return;
        }

        let activeFilter = 'all';

        function applyFilters() {
            const q = (searchInput ? searchInput.value : '').toLowerCase().trim();
            rows.forEach(function (row) {
                const state = row.getAttribute('data-state') || '';
                const urgency = row.getAttribute('data-urgency') || '';
                const text = (row.getAttribute('data-search') || '').toLowerCase();
                const matchFilter =
                    activeFilter === 'all' ||
                    (activeFilter === 'rush' && urgency === 'clinical_rush') ||
                    state === activeFilter;
                const matchSearch = !q || text.indexOf(q) !== -1;
                row.style.display = (matchFilter && matchSearch) ? 'flex' : 'none';
            });
        }

        function setFilter(nextFilter) {
            activeFilter = nextFilter || 'all';
            tabBtns.forEach(function (b) {
                b.classList.toggle('is-active', b.getAttribute('data-filter') === activeFilter);
            });
            railBtns.forEach(function (b) {
                b.classList.toggle('is-active', b.getAttribute('data-rail-filter') === activeFilter);
            });
            applyFilters();
        }

        tabBtns.forEach(function (btn) {
            btn.addEventListener('click', function () {
                setFilter(btn.getAttribute('data-filter'));
            });
        });

        railBtns.forEach(function (btn) {
            btn.addEventListener('click', function () {
                setFilter(btn.getAttribute('data-rail-filter'));
            });
        });

        if (searchInput) {
            searchInput.addEventListener('input', applyFilters);
        }
    }

    function hydrateVoicePlayer(playerEl) {
        if (!playerEl || playerEl.dataset.hydrated === '1') {
            return;
        }
        playerEl.dataset.hydrated = '1';

        const src = playerEl.getAttribute('data-audio-src');
        if (!src) {
            return;
        }

        const audio = new Audio(src);
        audio.preload = 'metadata';

        const playSvg = '<svg width="13" height="13" viewBox="0 0 24 24" fill="currentColor"><polygon points="6,4 20,12 6,20"/></svg>';
        const pauseSvg = '<svg width="13" height="13" viewBox="0 0 24 24" fill="currentColor"><rect x="6" y="4" width="4" height="16"/><rect x="14" y="4" width="4" height="16"/></svg>';

        const playBtn = document.createElement('button');
        playBtn.type = 'button';
        playBtn.className = 'ac-voice-play';
        playBtn.title = 'Play voice note';
        playBtn.innerHTML = playSvg;

        const barsWrap = document.createElement('div');
        barsWrap.className = 'ac-voice-bars';
        const bars = WAVE_HEIGHTS.map(function (h) {
            const bar = document.createElement('span');
            bar.className = 'ac-voice-bar';
            bar.style.height = h + 'px';
            barsWrap.appendChild(bar);
            return bar;
        });

        const durEl = document.createElement('span');
        durEl.className = 'ac-voice-dur';
        durEl.textContent = '0:00';

        playerEl.innerHTML = '';
        playerEl.appendChild(playBtn);
        playerEl.appendChild(barsWrap);
        playerEl.appendChild(durEl);

        function syncProgress() {
            const dur = audio.duration;
            const cur = audio.currentTime || 0;
            const ratio = (isFinite(dur) && dur > 0) ? Math.min(1, cur / dur) : 0;
            const filledCount = Math.round(ratio * bars.length);
            bars.forEach(function (b, idx) {
                b.classList.toggle('is-played', idx < filledCount);
            });
            if (!audio.paused) {
                durEl.textContent = formatSeconds(cur);
            } else if (isFinite(dur) && dur > 0) {
                durEl.textContent = formatSeconds(dur);
            }
        }

        audio.addEventListener('loadedmetadata', syncProgress);
        audio.addEventListener('timeupdate', syncProgress);
        audio.addEventListener('ended', function () {
            playBtn.innerHTML = playSvg;
            audio.currentTime = 0;
            syncProgress();
        });
        audio.addEventListener('pause', function () {
            playBtn.innerHTML = playSvg;
        });
        audio.addEventListener('play', function () {
            playBtn.innerHTML = pauseSvg;
            document.querySelectorAll('.ac-voice-player').forEach(function (other) {
                if (other !== playerEl && other._audio && !other._audio.paused) {
                    other._audio.pause();
                }
            });
        });

        playerEl._audio = audio;

        playBtn.addEventListener('click', function () {
            if (audio.paused) {
                audio.play().catch(function () {});
            } else {
                audio.pause();
            }
        });

        barsWrap.addEventListener('click', function (ev) {
            if (!isFinite(audio.duration) || audio.duration <= 0) {
                return;
            }
            const rect = barsWrap.getBoundingClientRect();
            const ratio = Math.max(0, Math.min(1, (ev.clientX - rect.left) / rect.width));
            audio.currentTime = ratio * audio.duration;
            syncProgress();
        });
    }

    function renderMessageNode(msg) {
        if (msg.is_system) {
            const sys = document.createElement('div');
            sys.className = 'ac-system-event';
            sys.textContent = msg.body + (msg.time ? ' · ' + msg.time : '');
            return sys;
        }

        const group = document.createElement('div');
        group.className = 'ac-msg-group' + (msg.is_me ? ' ac-msg-group--me' : '');

        const bubble = document.createElement('div');
        bubble.className = 'ac-msg';

        let html = '';
        if (!msg.is_me) {
            html += '<div class="ac-msg-author">' + escapeHtml(msg.author) + '</div>';
        }
        if (msg.audio_ids && msg.audio_ids.length) {
            msg.audio_ids.forEach(function (audId) {
                html += '<div class="ac-voice-player" data-audio-src="/web/content/' + encodeURIComponent(audId) + '"></div>';
            });
        } else if (msg.body) {
            html += '<div class="ac-msg-body">' + escapeHtml(msg.body) + '</div>';
        }
        if (msg.image_ids && msg.image_ids.length) {
            msg.image_ids.forEach(function (imgId) {
                html += '<img class="ac-msg-img" src="/web/image/' + encodeURIComponent(imgId) + '" alt="Seam photo"/>';
            });
        }
        bubble.innerHTML = html;

        const timeEl = document.createElement('div');
        timeEl.className = 'ac-msg-time';
        timeEl.textContent = msg.time || '';

        group.appendChild(bubble);
        group.appendChild(timeEl);

        group.querySelectorAll('.ac-voice-player').forEach(hydrateVoicePlayer);
        return group;
    }

    const STAGE_ORDER = ['draft', 'pattern', 'stitching', 'transit'];
    const STAGE_LABELS = {
        draft: 'Intake',
        pattern: 'Cutting',
        stitching: 'Sewing',
        transit: 'Ready',
    };

    function updateStagePills(newState) {
        const stageForm = document.getElementById('ac-stage-form');
        if (stageForm) {
            stageForm.setAttribute('data-current-state', newState);
        }
        const activeIdx = STAGE_ORDER.indexOf(newState);
        document.querySelectorAll('.ac-stage-pill[data-step-state]').forEach(function (btn) {
            const stepState = btn.getAttribute('data-step-state');
            const idx = STAGE_ORDER.indexOf(stepState);
            btn.classList.remove('is-active', 'is-done', 'is-proceed', 'is-next');
            if (activeIdx === -1) {
                btn.classList.add('is-done');
                btn.disabled = true;
                return;
            }
            if (idx === activeIdx) {
                btn.classList.add('is-active');
                btn.disabled = true;
            } else if (idx < activeIdx) {
                btn.classList.add('is-done');
                btn.disabled = true;
            } else {
                btn.classList.add('is-proceed');
                if (idx === activeIdx + 1) {
                    btn.classList.add('is-next');
                }
                btn.disabled = false;
            }
        });
    }

    function initDetail() {
        const thread = document.getElementById('ac-chat-thread');
        if (!thread) {
            return;
        }

        document.querySelectorAll('.ac-voice-player').forEach(hydrateVoicePlayer);

        function scrollToBottom() {
            thread.scrollTop = thread.scrollHeight;
        }
        scrollToBottom();

        // Right Order Specs Pane
        const infoPane = document.getElementById('ac-info-pane');
        const toggleBtn = document.getElementById('ac-toggle-specs');
        const closeBtn = document.getElementById('ac-close-specs');

        function setSpecsOpen(open) {
            if (!infoPane) {
                return;
            }
            infoPane.classList.toggle('is-closed', !open);
            if (toggleBtn) {
                toggleBtn.classList.toggle('is-active', open);
                toggleBtn.setAttribute('aria-expanded', open ? 'true' : 'false');
            }
        }

        if (infoPane) {
            setSpecsOpen(window.innerWidth >= 1100);
        }
        if (toggleBtn && infoPane) {
            toggleBtn.addEventListener('click', function () {
                setSpecsOpen(infoPane.classList.contains('is-closed'));
            });
        }
        if (closeBtn) {
            closeBtn.addEventListener('click', function () {
                setSpecsOpen(false);
            });
        }

        // Copy Specs (from either section button or quick-action circle)
        const specsRows = document.getElementById('ac-specs-copy-source');
        document.querySelectorAll('.js-copy-specs').forEach(function (btn) {
            btn.addEventListener('click', function () {
                if (!specsRows || !navigator.clipboard) {
                    return;
                }
                navigator.clipboard.writeText(specsRows.innerText.trim()).then(function () {
                    const labelEl = btn.querySelector('.js-copy-label') || btn;
                    const orig = labelEl.textContent;
                    labelEl.textContent = 'Copied';
                    setTimeout(function () { labelEl.textContent = orig; }, 1400);
                });
            });
        });

        // Photo Thumbnail Preview & Quick Attach trigger
        const photoInput = document.getElementById('ac-photo-input');
        const photoPreview = document.getElementById('ac-photo-preview');
        const photoThumb = document.getElementById('ac-photo-thumb');
        const photoName = document.getElementById('ac-photo-name');
        const photoClear = document.getElementById('ac-photo-clear');
        const quickPhotoBtn = document.getElementById('ac-quick-photo');
        let currentObjectUrl = null;

        if (quickPhotoBtn && photoInput) {
            quickPhotoBtn.addEventListener('click', function () {
                photoInput.click();
            });
        }

        function clearPhoto() {
            if (currentObjectUrl) {
                URL.revokeObjectURL(currentObjectUrl);
                currentObjectUrl = null;
            }
            if (photoInput) {
                photoInput.value = '';
            }
            if (photoThumb) {
                photoThumb.removeAttribute('src');
            }
            if (photoPreview) {
                photoPreview.classList.remove('is-visible');
            }
        }

        if (photoInput && photoPreview) {
            photoInput.addEventListener('change', function () {
                if (currentObjectUrl) {
                    URL.revokeObjectURL(currentObjectUrl);
                    currentObjectUrl = null;
                }
                if (photoInput.files && photoInput.files.length) {
                    const file = photoInput.files[0];
                    if (photoName) {
                        photoName.textContent = file.name;
                    }
                    if (photoThumb && file.type && file.type.indexOf('image/') === 0) {
                        currentObjectUrl = URL.createObjectURL(file);
                        photoThumb.src = currentObjectUrl;
                    }
                    photoPreview.classList.add('is-visible');
                } else {
                    clearPhoto();
                }
            });
        }

        if (photoClear) {
            photoClear.addEventListener('click', clearPhoto);
        }

        // Lightbox (Thread images + Shared Media images)
        const lightbox = document.getElementById('ac-lightbox');
        const lightboxImg = document.getElementById('ac-lightbox-img');
        const lightboxClose = document.getElementById('ac-lightbox-close');
        if (lightbox && lightboxImg) {
            document.addEventListener('click', function (ev) {
                const img = ev.target.closest('.ac-msg-img');
                const sharedImg = ev.target.closest('.js-open-image');
                const src = img ? img.src : (sharedImg ? sharedImg.getAttribute('data-img-src') : null);
                if (src) {
                    lightboxImg.src = src;
                    lightbox.classList.add('is-open');
                }
            });
            function closeLightbox() {
                lightbox.classList.remove('is-open');
                lightboxImg.removeAttribute('src');
            }
            if (lightboxClose) {
                lightboxClose.addEventListener('click', closeLightbox);
            }
            lightbox.addEventListener('click', function (ev) {
                if (ev.target === lightbox) {
                    closeLightbox();
                }
            });
            document.addEventListener('keydown', function (ev) {
                if (ev.key === 'Escape' && lightbox.classList.contains('is-open')) {
                    closeLightbox();
                }
            });
        }

        // AJAX Message Post & Voice Notes
        const msgForm = document.getElementById('ac-msg-form');
        const msgInput = document.getElementById('ac-msg-input');
        const sendBtn = document.getElementById('ac-send-btn');

        function postMessageFormData(formData, onDone) {
            formData.append('ajax', '1');
            return fetch(msgForm.action, {
                method: 'POST',
                body: formData,
                headers: { 'X-Requested-With': 'XMLHttpRequest' },
                credentials: 'same-origin',
            })
                .then(function (resp) {
                    if (!resp.ok) {
                        throw new Error('HTTP ' + resp.status);
                    }
                    const ct = resp.headers.get('content-type') || '';
                    if (ct.indexOf('application/json') === -1) {
                        window.location.reload();
                        return null;
                    }
                    return resp.json();
                })
                .then(function (data) {
                    if (!data) {
                        return;
                    }
                    if (data.message) {
                        thread.appendChild(renderMessageNode(data.message));
                        scrollToBottom();
                    }
                    if (onDone) {
                        onDone();
                    }
                });
        }

        if (msgForm) {
            msgForm.addEventListener('submit', function (ev) {
                const hasText = msgInput && msgInput.value.trim().length > 0;
                const hasPhoto = photoInput && photoInput.files && photoInput.files.length > 0;
                if (!hasText && !hasPhoto) {
                    ev.preventDefault();
                    return;
                }
                ev.preventDefault();
                if (sendBtn) {
                    sendBtn.disabled = true;
                }
                const formData = new FormData(msgForm);
                postMessageFormData(formData, function () {
                    if (msgInput) {
                        msgInput.value = '';
                    }
                    clearPhoto();
                })
                    .catch(function () {
                        msgForm.submit();
                    })
                    .finally(function () {
                        if (sendBtn) {
                            sendBtn.disabled = false;
                        }
                    });
            });
        }

        // Voice Note Recorder (MediaRecorder)
        const micBtn = document.getElementById('ac-mic-btn');
        const recBar = document.getElementById('ac-rec-bar');
        const recTimer = document.getElementById('ac-rec-timer');
        const recCancel = document.getElementById('ac-rec-cancel');
        const recSend = document.getElementById('ac-rec-send');
        const recError = document.getElementById('ac-rec-error');

        let mediaRecorder = null;
        let mediaStream = null;
        let audioChunks = [];
        let timerInterval = null;
        let recSeconds = 0;
        let shouldSendVoice = false;

        function showRecError(msg) {
            if (!recError) {
                return;
            }
            recError.textContent = msg;
            recError.classList.add('is-visible');
            setTimeout(function () {
                recError.classList.remove('is-visible');
            }, 4000);
        }

        function resetRecorderUI() {
            if (timerInterval) {
                clearInterval(timerInterval);
                timerInterval = null;
            }
            if (mediaStream) {
                mediaStream.getTracks().forEach(function (t) { t.stop(); });
                mediaStream = null;
            }
            mediaRecorder = null;
            audioChunks = [];
            recSeconds = 0;
            if (recTimer) {
                recTimer.textContent = '0:00';
            }
            if (recBar) {
                recBar.classList.remove('is-active');
            }
            if (msgForm) {
                msgForm.classList.remove('is-hidden');
            }
            if (recSend) {
                recSend.disabled = false;
            }
        }

        function pickMimeType() {
            const candidates = [
                'audio/webm;codecs=opus',
                'audio/webm',
                'audio/ogg;codecs=opus',
                'audio/mp4',
            ];
            if (!window.MediaRecorder || typeof window.MediaRecorder.isTypeSupported !== 'function') {
                return '';
            }
            for (let i = 0; i < candidates.length; i++) {
                if (window.MediaRecorder.isTypeSupported(candidates[i])) {
                    return candidates[i];
                }
            }
            return '';
        }

        if (micBtn && msgForm) {
            micBtn.addEventListener('click', function () {
                if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia || !window.MediaRecorder) {
                    showRecError('Voice recording is not supported in this browser.');
                    return;
                }
                navigator.mediaDevices.getUserMedia({ audio: true })
                    .then(function (stream) {
                        mediaStream = stream;
                        audioChunks = [];
                        shouldSendVoice = false;

                        const mimeType = pickMimeType();
                        mediaRecorder = mimeType
                            ? new MediaRecorder(stream, { mimeType: mimeType })
                            : new MediaRecorder(stream);

                        mediaRecorder.ondataavailable = function (ev) {
                            if (ev.data && ev.data.size > 0) {
                                audioChunks.push(ev.data);
                            }
                        };

                        mediaRecorder.onstop = function () {
                            const sendNow = shouldSendVoice;
                            const actualType = (mediaRecorder && mediaRecorder.mimeType) || mimeType || 'audio/webm';
                            const blobs = audioChunks.slice();
                            resetRecorderUI();

                            if (!sendNow || !blobs.length) {
                                return;
                            }
                            const ext = actualType.indexOf('ogg') !== -1 ? 'ogg'
                                : (actualType.indexOf('mp4') !== -1 ? 'm4a' : 'webm');
                            const voiceBlob = new Blob(blobs, { type: actualType });
                            const formData = new FormData();
                            const csrfInput = msgForm.querySelector('input[name="csrf_token"]');
                            if (csrfInput) {
                                formData.append('csrf_token', csrfInput.value);
                            }
                            formData.append('voice', voiceBlob, 'voice_note_' + Date.now() + '.' + ext);

                            postMessageFormData(formData).catch(function () {
                                showRecError('Could not upload voice note. Please retry.');
                            });
                        };

                        mediaRecorder.start();
                        if (msgForm) {
                            msgForm.classList.add('is-hidden');
                        }
                        if (recBar) {
                            recBar.classList.add('is-active');
                        }
                        recSeconds = 0;
                        if (recTimer) {
                            recTimer.textContent = '0:00';
                        }
                        timerInterval = setInterval(function () {
                            recSeconds += 1;
                            if (recTimer) {
                                recTimer.textContent = formatSeconds(recSeconds);
                            }
                        }, 1000);
                    })
                    .catch(function () {
                        showRecError('Microphone permission denied or unavailable.');
                    });
            });
        }

        if (recCancel) {
            recCancel.addEventListener('click', function () {
                shouldSendVoice = false;
                if (mediaRecorder && mediaRecorder.state !== 'inactive') {
                    mediaRecorder.stop();
                } else {
                    resetRecorderUI();
                }
            });
        }

        if (recSend) {
            recSend.addEventListener('click', function () {
                shouldSendVoice = true;
                recSend.disabled = true;
                if (mediaRecorder && mediaRecorder.state !== 'inactive') {
                    mediaRecorder.stop();
                } else {
                    resetRecorderUI();
                }
            });
        }

        // Forward-Only Stage Proceed Buttons with Permanent Change Confirmation
        const stageForm = document.getElementById('ac-stage-form');
        const confirmModal = document.getElementById('ac-stage-confirm-modal');
        const confirmTitle = document.getElementById('ac-confirm-title');
        const confirmBody = document.getElementById('ac-confirm-body');
        const confirmCancel = document.getElementById('ac-confirm-cancel');
        const confirmProceed = document.getElementById('ac-confirm-proceed');

        if (stageForm) {
            let pendingTargetState = null;

            function submitStageAdvance(targetState) {
                if (confirmProceed) {
                    confirmProceed.disabled = true;
                    confirmProceed.textContent = 'Updating...';
                }
                const formData = new FormData(stageForm);
                formData.set('target_state', targetState);
                formData.append('ajax', '1');

                fetch(stageForm.action, {
                    method: 'POST',
                    body: formData,
                    headers: { 'X-Requested-With': 'XMLHttpRequest' },
                    credentials: 'same-origin',
                })
                    .then(function (resp) {
                        if (!resp.ok) {
                            throw new Error('HTTP ' + resp.status);
                        }
                        const ct = resp.headers.get('content-type') || '';
                        if (ct.indexOf('application/json') === -1) {
                            window.location.reload();
                            return null;
                        }
                        return resp.json();
                    })
                    .then(function (data) {
                        if (!data) {
                            return;
                        }
                        if (data.state) {
                            updateStagePills(data.state);
                        }
                        if (data.message) {
                            thread.appendChild(renderMessageNode(data.message));
                            scrollToBottom();
                        }
                    })
                    .catch(function () {
                        window.location.reload();
                    })
                    .finally(function () {
                        closeConfirmModal();
                    });
            }

            function closeConfirmModal() {
                pendingTargetState = null;
                if (confirmProceed) {
                    confirmProceed.disabled = false;
                    confirmProceed.textContent = 'Yes, Proceed';
                }
                if (confirmModal) {
                    confirmModal.classList.remove('is-open');
                }
            }

            function openConfirmModal(targetState, currentState) {
                const targetLabel = STAGE_LABELS[targetState] || targetState;
                const currentLabel = STAGE_LABELS[currentState] || currentState;
                const orderName = stageForm.getAttribute('data-order-name') || 'this order';

                if (!confirmModal) {
                    if (window.confirm('Are you sure you want to proceed ' + orderName + ' to ' + targetLabel + '? This is a permanent change.')) {
                        submitStageAdvance(targetState);
                    }
                    return;
                }

                pendingTargetState = targetState;
                if (confirmTitle) {
                    confirmTitle.textContent = 'Proceed to ' + targetLabel + '?';
                }
                if (confirmBody) {
                    confirmBody.textContent =
                        'Are you sure you want to move ' + orderName +
                        ' from ' + currentLabel + ' to ' + targetLabel + '?';
                }
                confirmModal.classList.add('is-open');
            }

            if (confirmCancel) {
                confirmCancel.addEventListener('click', closeConfirmModal);
            }
            if (confirmProceed) {
                confirmProceed.addEventListener('click', function () {
                    if (!pendingTargetState) {
                        closeConfirmModal();
                        return;
                    }
                    const nextState = pendingTargetState;
                    submitStageAdvance(nextState);
                });
            }
            if (confirmModal) {
                confirmModal.addEventListener('click', function (ev) {
                    if (ev.target === confirmModal) {
                        closeConfirmModal();
                    }
                });
                document.addEventListener('keydown', function (ev) {
                    if (ev.key === 'Escape' && confirmModal.classList.contains('is-open')) {
                        closeConfirmModal();
                    }
                });
            }

            stageForm.addEventListener('submit', function (ev) {
                const submitter = ev.submitter;
                if (!submitter || !submitter.value) {
                    return;
                }
                ev.preventDefault();

                const currentState = stageForm.getAttribute('data-current-state') || '';
                const targetState = submitter.value;
                const curIdx = STAGE_ORDER.indexOf(currentState);
                const tgtIdx = STAGE_ORDER.indexOf(targetState);
                if (tgtIdx === -1 || (curIdx !== -1 && tgtIdx <= curIdx)) {
                    return;
                }
                openConfirmModal(targetState, currentState);
            });
        }
    }

    document.addEventListener('DOMContentLoaded', function () {
        initQueue();
        initDetail();
    });
})();
