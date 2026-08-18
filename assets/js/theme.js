(function () {
  const btn = document.getElementById('theme-toggle');
  if (!btn) return;

  const sunIcon = btn.querySelector('.sun-icon');
  const moonIcon = btn.querySelector('.moon-icon');
  const mq = window.matchMedia('(prefers-color-scheme: light)');

  function updateIcons(t) {
    if (t === 'light') {
      sunIcon.style.display = 'none';
      moonIcon.style.display = 'block';
    } else {
      sunIcon.style.display = 'block';
      moonIcon.style.display = 'none';
    }
  }

  function getTheme() {
    return localStorage.getItem('theme') || (mq.matches ? 'light' : 'dark');
  }

  function applyTheme(t) {
    document.documentElement.setAttribute('data-theme', t);
    updateIcons(t);
  }

  applyTheme(getTheme());

  mq.addEventListener('change', function (e) {
    if (!localStorage.getItem('theme')) applyTheme(e.matches ? 'light' : 'dark');
  });

  btn.addEventListener('click', function () {
    var next = getTheme() === 'dark' ? 'light' : 'dark';
    localStorage.setItem('theme', next);
    applyTheme(next);
  });
})();
