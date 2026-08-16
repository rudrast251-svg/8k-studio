document.addEventListener('DOMContentLoaded', function () {
  // Mobile nav toggle
  var toggle = document.querySelector('.nav-toggle');
  var links = document.querySelector('.nav-links');
  if (toggle && links) {
    toggle.addEventListener('click', function () {
      links.classList.toggle('open');
    });
  }

  // FAQ accordion
  document.querySelectorAll('.faq-q').forEach(function (q) {
    q.addEventListener('click', function () {
      q.closest('.faq-item').classList.toggle('open');
    });
  });

  // Dropzone preview
  document.querySelectorAll('.dropzone').forEach(function (zone) {
    var input = zone.querySelector('input[type=file]');
    var label = zone.querySelector('.dz-filename');
    if (!input) return;
    input.addEventListener('change', function () {
      if (input.files && input.files[0] && label) {
        label.textContent = input.files[0].name + ' (' + (input.files[0].size / (1024 * 1024)).toFixed(1) + ' MB)';
      }
    });
    ['dragover', 'dragleave', 'drop'].forEach(function (evt) {
      zone.addEventListener(evt, function (e) {
        e.preventDefault();
        zone.classList.toggle('dragover', evt === 'dragover');
      });
    });
    zone.addEventListener('drop', function (e) {
      if (e.dataTransfer.files.length) {
        input.files = e.dataTransfer.files;
        input.dispatchEvent(new Event('change'));
      }
    });
  });

  // Asset picker (upload page / editor page)
  document.querySelectorAll('.asset-picker-grid').forEach(function (grid) {
    var hidden = document.querySelector(grid.dataset.target);
    grid.querySelectorAll('.asset-thumb').forEach(function (thumb) {
      thumb.addEventListener('click', function () {
        grid.querySelectorAll('.asset-thumb').forEach(function (t) { t.classList.remove('selected'); });
        thumb.classList.add('selected');
        if (hidden) hidden.value = thumb.dataset.assetId;
      });
    });
  });

  // Notifications dropdown
  var notifBtn = document.querySelector('.notif-btn');
  var notifDropdown = document.querySelector('.notif-dropdown');
  if (notifBtn && notifDropdown) {
    notifBtn.addEventListener('click', function (e) {
      e.stopPropagation();
      notifDropdown.classList.toggle('open');
      if (notifDropdown.classList.contains('open')) {
        fetch('/dashboard/notifications/mark-read/', {
          method: 'POST',
          headers: { 'X-CSRFToken': getCookie('csrftoken') },
        }).then(function () {
          var dot = document.querySelector('.notif-dot');
          if (dot) dot.classList.remove('show');
        });
      }
    });
    document.addEventListener('click', function () { notifDropdown.classList.remove('open'); });
    notifDropdown.addEventListener('click', function (e) { e.stopPropagation(); });
  }

  function refreshNotifications() {
    fetch('/dashboard/notifications/').then(function (r) { return r.json(); }).then(function (data) {
      var dot = document.querySelector('.notif-dot');
      if (dot) dot.classList.toggle('show', data.unread_count > 0);
      var list = document.querySelector('.notif-dropdown .notif-list');
      if (!list) return;
      if (!data.notifications.length) {
        list.innerHTML = '<div class="notif-empty">No notifications yet.</div>';
        return;
      }
      list.innerHTML = data.notifications.map(function (n) {
        return '<div class="notif-item ' + (n.is_read ? '' : 'unread') + '">' + n.message + '<span>' + new Date(n.created_at).toLocaleString() + '</span></div>';
      }).join('');
    }).catch(function () {});
  }
  if (document.querySelector('.notif-wrap')) {
    refreshNotifications();
    setInterval(refreshNotifications, 15000);
  }

  // Job status polling on job detail page
  var statusEl = document.querySelector('[data-job-status-url]');
  if (statusEl) {
    var url = statusEl.dataset.jobStatusUrl;
    var poll = function () {
      fetch(url).then(function (r) { return r.json(); }).then(function (data) {
        var badge = document.querySelector('[data-job-badge]');
        var fill = document.querySelector('[data-progress-fill]');
        if (fill) fill.style.width = data.progress_percent + '%';
        if (badge && badge.dataset.status !== data.status) {
          location.reload();
          return;
        }
        if (data.status === 'processing' || data.status === 'uploaded') {
          setTimeout(poll, 2500);
        }
      }).catch(function () { setTimeout(poll, 4000); });
    };
    poll();
  }

  function getCookie(name) {
    var value = '; ' + document.cookie;
    var parts = value.split('; ' + name + '=');
    if (parts.length === 2) return parts.pop().split(';').shift();
    return '';
  }
});
