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
        if (msg.body) {
            html += '<div class="ac-msg-body">' + escapeHtml(msg.body) + '</div>';
        }
        if (msg.image_ids && msg.image_ids.length) {
            msg.image_ids.forEach(function (imgId) {
                html += '<img class="ac-msg-img" src="/web/image/' + encodeURIComponent(imgId) + '" alt="Seam photo"/>';
            });
        }
        html += '<div class="ac-msg-time">' + escapeHtml(msg.time) + '</div>';

        wrap.innerHTML = html;
        return wrap;
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

        // Toggle Specs Panel
        const toggleBtn = document.getElementById('ac-toggle-specs');
        const specsPanel = document.getElementById('ac-specs-panel');
        if (toggleBtn && specsPanel) {
            toggleBtn.addEventListener('click', function () {
                const hidden = specsPanel.classList.toggle('is-hidden');
                toggleBtn.textContent = hidden ? 'View Specs' : 'Hide Specs';
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
                        return resp.json();
                    })
                    .then(function (data) {
                        if (data && data.message) {
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

        // Stage Dropdown Auto-Update
        const stageForm = document.getElementById('ac-stage-form');
        const stageSelect = document.getElementById('ac-stage-select');
        if (stageForm && stageSelect) {
            stageSelect.addEventListener('change', function () {
                const formData = new FormData(stageForm);
                formData.append('ajax', '1');
                stageSelect.disabled = true;

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
                        return resp.json();
                    })
                    .then(function (data) {
                        if (data && data.message) {
                            thread.appendChild(renderMessageNode(data.message));
                            scrollToBottom();
                        }
                    })
                    .catch(function () {
                        stageForm.submit();
                    })
                    .finally(function () {
                        stageSelect.disabled = false;
                    });
            });
        }
    }

    document.addEventListener('DOMContentLoaded', function () {
        initQueue();
        initDetail();
    });
})();
