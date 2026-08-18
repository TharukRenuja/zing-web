(function () {
  var toggle = document.getElementById('sidebar-toggle');
  var sidebar = document.getElementById('sidebar');
  var overlay = document.getElementById('sidebar-overlay');
  var closeBtn = document.getElementById('sidebar-close');

  function openSidebar() {
    sidebar.classList.add('open');
    overlay.classList.add('active');
    document.body.style.overflow = 'hidden';
  }

  function closeSidebar() {
    sidebar.classList.remove('open');
    overlay.classList.remove('active');
    document.body.style.overflow = '';
  }

  if (toggle) {
    toggle.addEventListener('click', function (e) {
      e.stopPropagation();
      if (sidebar.classList.contains('open')) closeSidebar();
      else openSidebar();
    });
  }

  if (overlay) overlay.addEventListener('click', closeSidebar);
  if (closeBtn) closeBtn.addEventListener('click', closeSidebar);

  if (sidebar) {
    sidebar.querySelectorAll('a').forEach(function (link) {
      link.addEventListener('click', closeSidebar);
    });
  }
})();

function copyCode(btn) {
  var code = btn.parentElement.querySelector('pre code');
  var text = code.textContent;
  navigator.clipboard.writeText(text).then(function () {
    var orig = btn.innerHTML;
    btn.innerHTML = '<i class="fa-solid fa-check"></i> Copied!';
    setTimeout(function () { btn.innerHTML = orig; }, 1500);
  }).catch(function () {});
}
