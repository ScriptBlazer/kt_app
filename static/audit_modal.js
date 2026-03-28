(function () {
    function closeAuditModal() {
        var modal = document.getElementById('audit-detail-modal');
        if (!modal) return;
        modal.style.display = 'none';
        modal.setAttribute('aria-hidden', 'true');
    }

    function escapeHtml(text) {
        if (text == null) return '';
        var div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    function openAuditModal(title, innerHtml) {
        var modal = document.getElementById('audit-detail-modal');
        var titleEl = document.getElementById('audit-modal-title');
        var bodyEl = document.getElementById('audit-modal-body');
        if (!modal || !titleEl || !bodyEl) return;
        titleEl.textContent = title;
        bodyEl.innerHTML = innerHtml;
        modal.style.display = 'flex';
        modal.setAttribute('aria-hidden', 'false');
    }

    function showLoading(title) {
        openAuditModal(title, '<p class="audit-loading">Loading…</p>');
    }

    function renderAdded(data) {
        var who = escapeHtml(data.added_by || 'Unknown');
        var when = escapeHtml(data.added_at || 'Unknown');
        return (
            '<div class="audit-panel audit-panel--added">' +
            '<div class="audit-section">' +
            '<div class="audit-section-label">Recorded by</div>' +
            '<div class="audit-section-value">' + who + '</div>' +
            '</div>' +
            '<div class="audit-section">' +
            '<div class="audit-section-label">When</div>' +
            '<div class="audit-section-value">' + when + '</div>' +
            '</div>' +
            '</div>'
        );
    }

    function renderChangeRows(changes) {
        if (!changes || !changes.length) {
            return '<p class="audit-no-field-changes">No field changes were recorded for this save.</p>';
        }
        var rows = changes.map(function (c) {
            var label = escapeHtml(c.label || '');
            var oldV = escapeHtml(c.old != null ? c.old : '—');
            var newV = escapeHtml(c.new != null ? c.new : '—');
            return (
                '<li class="audit-change-item">' +
                '<div class="audit-change-label">' + label + '</div>' +
                '<div class="audit-change-values">' +
                '<span class="audit-ch-old" title="Previous">' + oldV + '</span>' +
                '<span class="audit-ch-arrow" aria-hidden="true">→</span>' +
                '<span class="audit-ch-new" title="Updated">' + newV + '</span>' +
                '</div></li>'
            );
        }).join('');
        return '<ul class="audit-change-list">' + rows + '</ul>';
    }

    function renderEdited(data) {
        var edits = data.edits || [];
        if (!edits.length) {
            return '<p class="audit-muted">No edit history recorded yet.</p>';
        }
        var blocks = edits.map(function (e) {
            var u = escapeHtml(e.user || 'Unknown');
            var t = escapeHtml(e.at || 'Unknown');
            var changes = e.changes || [];
            return (
                '<article class="audit-edit-block">' +
                '<header class="audit-edit-header">' +
                '<span class="audit-edit-user">' + u + '</span>' +
                '<span class="audit-edit-time">' + t + '</span>' +
                '</header>' +
                '<div class="audit-edit-body">' + renderChangeRows(changes) + '</div>' +
                '</article>'
            );
        }).join('');
        return '<div class="audit-history">' + blocks + '</div>';
    }

    function handleTrigger(el) {
        var url = el.getAttribute('data-audit-url');
        var mode = el.getAttribute('data-audit-mode');
        if (!url) return;
        var title = mode === 'edited' ? 'Edit history' : 'Added';
        showLoading(title);
        fetch(url, { credentials: 'same-origin', headers: { Accept: 'application/json' } })
            .then(function (r) {
                if (!r.ok) throw new Error('Failed to load');
                return r.json();
            })
            .then(function (data) {
                var html = mode === 'edited' ? renderEdited(data) : renderAdded(data);
                openAuditModal(title, html);
            })
            .catch(function () {
                openAuditModal(title, '<p class="audit-muted">Unknown</p>');
            });
    }

    document.addEventListener('click', function (e) {
        var el = e.target.closest('.audit-tag-clickable');
        if (el) {
            e.preventDefault();
            handleTrigger(el);
            return;
        }
        if (e.target.id === 'audit-modal-close' || e.target.closest('#audit-modal-close')) {
            closeAuditModal();
            return;
        }
        var modal = document.getElementById('audit-detail-modal');
        if (modal && e.target === modal) {
            closeAuditModal();
        }
    });

    document.addEventListener('keydown', function (e) {
        if (e.key === 'Escape') {
            closeAuditModal();
        }
        if (e.key !== 'Enter' && e.key !== ' ') return;
        var el = e.target.closest('.audit-tag-clickable');
        if (!el) return;
        e.preventDefault();
        handleTrigger(el);
    });

    var closeBtn = document.getElementById('audit-modal-close');
    if (closeBtn) {
        closeBtn.addEventListener('keydown', function (e) {
            if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                closeAuditModal();
            }
        });
    }
})();
