(function () {
  var hoveredCarousel = null;

  document.querySelectorAll('.ext-carousel').forEach(function (carousel) {
    var inner = carousel.querySelector('.ext-carousel-inner');
    var items = carousel.querySelectorAll('.ext-carousel-item');
    var dotsWrap = carousel.querySelector('.ext-carousel-dots');
    var btns = carousel.querySelectorAll('.ext-carousel-btn');
    var total = items.length;
    var current = 0;
    var programmatic = false;

    // Build dots
    items.forEach(function (_, i) {
      var dot = document.createElement('div');
      dot.className = 'ext-carousel-dot' + (i === 0 ? ' active' : '');
      dot.addEventListener('click', function () { goTo(i); });
      dotsWrap.appendChild(dot);
    });

    var dots = dotsWrap.querySelectorAll('.ext-carousel-dot');

    function updateDots(idx) {
      dots.forEach(function (d, i) { d.classList.toggle('active', i === idx); });
    }

    function goTo(idx) {
      if (total === 0) return;
      current = ((idx % total) + total) % total;
      programmatic = true;
      updateDots(current);
      inner.scrollTo({ left: items[current].offsetLeft - (inner.clientWidth - items[current].offsetWidth) / 2, behavior: 'smooth' });
      setTimeout(function () { programmatic = false; }, 400);
    }

    btns.forEach(function (btn) {
      btn.addEventListener('click', function () {
        var dir = parseInt(btn.dataset.dir);
        goTo(current + dir);
      });
    });

    carousel.addEventListener('mouseenter', function () { hoveredCarousel = carousel; });
    carousel.addEventListener('mouseleave', function () { if (hoveredCarousel === carousel) hoveredCarousel = null; });

    inner.addEventListener('scroll', function () {
      if (programmatic) return;
      var scrollLeft = inner.scrollLeft;
      var mid = scrollLeft + inner.clientWidth / 2;
      var closest = 0, closestDist = Infinity;
      items.forEach(function (item, i) {
        var dist = Math.abs((item.offsetLeft + item.offsetWidth / 2) - mid);
        if (dist < closestDist) { closestDist = dist; closest = i; }
      });
      if (closest !== current) {
        current = closest;
        updateDots(current);
      }
    });
  });

  // Arrow key navigation — scoped to hovered carousel
  document.addEventListener('keydown', function (e) {
    if (!hoveredCarousel) return;
    if (e.key === 'ArrowLeft' || e.key === 'ArrowRight') {
      e.preventDefault();
      var inner = hoveredCarousel.querySelector('.ext-carousel-inner');
      var items = hoveredCarousel.querySelectorAll('.ext-carousel-item');
      var dots = hoveredCarousel.querySelectorAll('.ext-carousel-dot');
      var total = items.length;
      var scrollLeft = inner.scrollLeft;
      var mid = scrollLeft + inner.clientWidth / 2;
      var current = 0, closestDist = Infinity;
      items.forEach(function (item, i) {
        var dist = Math.abs((item.offsetLeft + item.offsetWidth / 2) - mid);
        if (dist < closestDist) { closestDist = dist; current = i; }
      });
      var dir = e.key === 'ArrowLeft' ? -1 : 1;
      var next = ((current + dir) % total + total) % total;
      inner.scrollTo({ left: items[next].offsetLeft - (inner.clientWidth - items[next].offsetWidth) / 2, behavior: 'smooth' });
      dots.forEach(function (d, i) { d.classList.toggle('active', i === next); });
    }
  });

  // Capture wheel on hovered carousel → scroll images instead of page
  document.addEventListener('wheel', function (e) {
    var target = e.target.closest('.ext-carousel');
    if (!target) return;
    e.preventDefault();
    var inner = target.querySelector('.ext-carousel-inner');
    var items = target.querySelectorAll('.ext-carousel-item');
    var dots = target.querySelectorAll('.ext-carousel-dot');
    var total = items.length;
    if (total === 0) return;
    var scrollLeft = inner.scrollLeft;
    var mid = scrollLeft + inner.clientWidth / 2;
    var current = 0, closestDist = Infinity;
    items.forEach(function (item, i) {
      var dist = Math.abs((item.offsetLeft + item.offsetWidth / 2) - mid);
      if (dist < closestDist) { closestDist = dist; current = i; }
    });
    var dir = e.deltaY > 0 ? 1 : -1;
    var next = ((current + dir) % total + total) % total;
    inner.scrollTo({ left: items[next].offsetLeft - (inner.clientWidth - items[next].offsetWidth) / 2, behavior: 'smooth' });
    dots.forEach(function (d, i) { d.classList.toggle('active', i === next); });
  }, { passive: false });
})();
