(function () {
    'use strict';

    function initQueue() {
        const searchInput = document.getElementById('ac-order-search');
        const rows = document.querySelectorAll('.ac-order-row');
        if (!searchInput) {
            return;
        }
        searchInput.addEventListener('input', function () {
            const q = (searchInput.value || '').toLowerCase().trim();
            rows.forEach(function (row) {
                const text = (row.getAttribute('data-search') || '').toLowerCase();
                row.style.display = (!q || text.indexOf(q) !== -1) ? 'flex' : 'none';
            });
        });
    }

    function escapeHtml(str) {
        const div = document.createElement('div');
        div.textContent = str == null ? '' : String(str);
        return div.innerHTML;
    }

    function renderMessageNode(msg) {
        if (msg.is_system) {
            const sys = document.createElement('div');
            sys.className = 'ac-system-event';
            sys.textContent = msg.body + (msg.time ? ' · ' + msg.time : '');
            return sys;
        }

        const wrap = document.createElement('div');
        wrap.className = 'ac-msg' + (msg.is_me ? ' ac-msg--me' : '');

        let html = '';
        if (!msg.is_me) {
            html += '<div class="ac-msg-author">' + escapeHtml(msg.author) + '</div>';
        }
        if (msg.image_ids && msg.image_ids.length) {
            msg.image_ids.forEach(function (imgId) {
                html += '<img class="ac-msg-img" src="/web/image/' + encodeURIComponent(imgId) + '" alt="Seam photo"/>';
            });
        }
        html += '<div class="ac-msg-content">';
        if (msg.body) {
            html += '<span class="ac-msg-body">' + escapeHtml(msg.body) + '</span>';
        }
        html += '<span class="ac-msg-time">' + escapeHtml(msg.time) + '</span>';
        html += '</div>';

        wrap.innerHTML = html;
        return wrap;
    }

    function updateStagePills(newState) {
        const order = ['draft', 'pattern', 'stitching', 'transit'];
        const activeIdx = order.indexOf(newState);
        document.querySelectorAll('.ac-stage-pill[data-step-state]').forEach(function (btn) {
            const stepState = btn.getAttribute('data-step-state');
            const idx = order.indexOf(stepState);
            btn.classList.remove('is-active', 'is-done');
            btn.disabled = false;
            if (idx === activeIdx) {
                btn.classList.add('is-active');
                btn.disabled = true;
            } else if (activeIdx !== -1 && idx !== -1 && idx < activeIdx) {
                btn.classList.add('is-done');
            }
        });
    }

    function initDetail() {
        const thread = document.getElementById('ac-chat-thread');
        if (!thread) {
            return;
        }

        function scrollToBottom() {
            thread.scrollTop = thread.scrollHeight;
        }
        scrollToBottom();

        // WhatsApp-Style Right Order Specs Pane
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

        // Copy Specs
        const copyBtn = document.getElementById('ac-copy-specs');
        const specsRows = document.getElementById('ac-specs-copy-source');
        if (copyBtn && specsRows && navigator.clipboard) {
            copyBtn.addEventListener('click', function () {
                navigator.clipboard.writeText(specsRows.innerText.trim()).then(function () {
                    const orig = copyBtn.textContent;
                    copyBtn.textContent = 'Copied';
                    setTimeout(function () { copyBtn.textContent = orig; }, 1400);
                });
            });
        }

        // Photo Thumbnail Preview
        const photoInput = document.getElementById('ac-photo-input');
        const photoPreview = document.getElementById('ac-photo-preview');
        const photoThumb = document.getElementById('ac-photo-thumb');
        const photoName = document.getElementById('ac-photo-name');
        const photoClear = document.getElementById('ac-photo-clear');
        let currentObjectUrl = null;

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

        // Lightbox
        const lightbox = document.getElementById('ac-lightbox');
        const lightboxImg = document.getElementById('ac-lightbox-img');
        const lightboxClose = document.getElementById('ac-lightbox-close');
        if (lightbox && lightboxImg) {
            thread.addEventListener('click', function (ev) {
                const img = ev.target.closest('.ac-msg-img');
                if (img) {
                    lightboxImg.src = img.src;
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

        // AJAX Message Post
        const msgForm = document.getElementById('ac-msg-form');
        const msgInput = document.getElementById('ac-msg-input');
        const sendBtn = document.getElementById('ac-send-btn');
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
                formData.append('ajax', '1');

                fetch(msgForm.action, {
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

        // Segmented Stage Pills
        const stageForm = document.getElementById('ac-stage-form');
        if (stageForm) {
            stageForm.addEventListener('submit', function (ev) {
                const submitter = ev.submitter;
                if (!submitter || !submitter.value) {
                    return;
                }
                ev.preventDefault();
                const formData = new FormData(stageForm);
                formData.set('target_state', submitter.value);
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
                    });
            });
        }
    }

    document.addEventListener('DOMContentLoaded', function () {
        initQueue();
        initDetail();
    });
})();
