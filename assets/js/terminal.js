(function () {
  var body = document.getElementById('terminal-body');
  if (!body) return;

  var allLines = Array.from(body.children).filter(function (c) { return c.tagName === 'DIV'; });
  var cmdLine = document.getElementById('tui-cmd');
  var cmdText = document.getElementById('tui-cmd-text');
  var bar = body.querySelector('[data-tui="bar"]');

  var CMD = 'zing tui zing.tharuk.pro/download/zing-v0.2.6-x86_64-mac.dmg';
  var TOTAL_BYTES = 10800332;
  var FINAL_DL = 4400000;
  var CHAR_MS = 35;
  var LINE_DELAY = 70;
  var SIM_MS = 8000;
  var HOLD_MS = 4000;

  var el = function (sel) { return body.querySelector('[data-tui="' + sel + '"]'); };
  var prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  function fmtBytes(b) {
    if (b === 0) return '0 B';
    if (b < 1024) return b + ' B';
    if (b < 1048576) return (b / 1024).toFixed(1) + ' KB';
    return (b / 1048576).toFixed(1) + ' MB';
  }

  function fmtSpeed(bps) {
    if (!bps || bps < 100) return '--';
    if (bps < 1048576) return (bps / 1024).toFixed(1) + ' KB/s';
    return (bps / 1048576).toFixed(1) + ' MB/s';
  }

  function fmtPct(p) { return Math.round(p) + '%'; }
  function pad(s, n) { return String(s).padEnd(n); }

  function hideAll() { allLines.forEach(function (l) { l.classList.remove('is-visible'); }); }
  function showAll() { allLines.forEach(function (l) { l.classList.add('is-visible'); }); }
  function hideCmd() { cmdLine.classList.remove('is-visible'); }
  function showCmd() { cmdLine.classList.add('is-visible'); }

  function resetAll() {
    hideAll(); hideCmd();
    cmdText.textContent = '';
    bar.style.setProperty('--bar-fill', '0%');
    el('dl-title').textContent = pad('0 B', 7);
    el('dl-main').textContent = pad('0 B', 7);
    el('dl-stats').textContent = pad('0 B', 7);
    el('dl-bar').textContent = pad('0 B', 7);
    el('speed-title').textContent = pad('--', 10);
    el('speed-main').textContent = pad('--', 10);
    el('speed-stats').textContent = pad('--', 10);
    el('speed-bar').textContent = pad('--', 10);
    el('pct-main').textContent = pad('0%', 4);
    el('pct-bar').textContent = pad(' 0%', 5);
    el('eta').textContent = pad('--', 3);
    el('blocks').textContent = pad('0/165', 7);
    el('inflight').textContent = pad('0', 3);
    el('peak').textContent = pad('--', 8);
    el('peak-bar').textContent = pad('--', 8);
    el('running').textContent = pad('0 running', 9);
    el('file-status').textContent = pad('idle', 11);
    el('file-status').className = 't-dim';
    for (var i = 0; i < 3; i++) {
      el('conn' + i + '-speed').textContent = pad('-', 17);
      el('conn' + i + '-speed').className = 't-green';
      el('conn' + i + '-bytes').textContent = pad('0 B', 15);
      el('conn' + i + '-time').textContent = pad('0s', 13);
      el('conn' + i + '-state').textContent = pad('\u2022 idle', 8);
      el('conn' + i + '-state').className = 't-yellow';
    }
  }

  function setFinal() {
    bar.style.setProperty('--bar-fill', '40.7%');
    el('dl-title').textContent = pad('4.4 MB', 7);
    el('dl-main').textContent = pad('4.4 MB', 7);
    el('dl-stats').textContent = pad('4.4 MB', 7);
    el('dl-bar').textContent = pad('4.4 MB', 7);
    el('speed-title').textContent = pad('510.1 KB/s', 10);
    el('speed-main').textContent = pad('510.1 KB/s', 10);
    el('speed-stats').textContent = pad('510.1 KB/s', 10);
    el('speed-bar').textContent = pad('510.1 KB/s', 10);
    el('pct-main').textContent = pad('41%', 4);
    el('pct-bar').textContent = pad(' 41%', 5);
    el('eta').textContent = pad('12s', 3);
    el('blocks').textContent = pad('77/165', 7);
    el('inflight').textContent = pad('15', 3);
    el('peak').textContent = pad('1.4 MB/s', 8);
    el('peak-bar').textContent = pad('1.4 MB/s', 8);
    el('running').textContent = pad('1 running', 9);
    el('file-status').textContent = pad('downloading', 11);
    el('file-status').className = 't-green';
    el('conn0-speed').textContent = pad('62.7 KB/s', 17);
    el('conn0-speed').className = 't-green';
    el('conn0-bytes').textContent = pad('1.0 MB', 15);
    el('conn0-time').textContent = pad('7s', 13);
    el('conn0-state').textContent = pad('\u2022 active', 8);
    el('conn0-state').className = 't-green';
    el('conn1-speed').textContent = pad('-', 17);
    el('conn1-speed').className = 't-green';
    el('conn1-bytes').textContent = pad('0 B', 15);
    el('conn1-time').textContent = pad('6s', 13);
    el('conn1-state').textContent = pad('\u2022 idle', 8);
    el('conn1-state').className = 't-yellow';
    el('conn2-speed').textContent = pad('63.8 KB/s', 17);
    el('conn2-speed').className = 't-green';
    el('conn2-bytes').textContent = pad('319.1 KB', 15);
    el('conn2-time').textContent = pad('6s', 13);
    el('conn2-state').textContent = pad('\u2022 active', 8);
    el('conn2-state').className = 't-green';
  }

  function sleep(ms) { return new Promise(function (r) { setTimeout(r, ms); }); }

  async function typeCommand() {
    hideAll();
    showCmd();
    cmdLine.classList.add('is-visible');
    cmdText.textContent = '';
    for (var i = 0; i < CMD.length; i++) {
      cmdText.textContent += CMD[i];
      await sleep(CHAR_MS);
    }
  }

  async function revealTui() {
    hideCmd();
    for (var idx = 0; idx < allLines.length; idx++) {
      allLines[idx].classList.add('is-visible');
      await sleep(LINE_DELAY);
    }
  }

  async function simulateDownload() {
    var conns = [
      { activateAt: 500, finalSpeed: 62700, finalBytes: 1048576 },
      { activateAt: Infinity, finalSpeed: 0, finalBytes: 650240 },
      { activateAt: 2000, finalSpeed: 63800, finalBytes: 326789 }
    ];
    conns.forEach(function (c) { c.active = false; c.speed = 0; c.bytes = 0; });

    var peakSeen = 0;

    await new Promise(function (resolve) {
      var startTime = null;

      function frame(t) {
        if (!startTime) startTime = t;
        var elapsed = t - startTime;
        var progress = Math.min(elapsed / SIM_MS, 1);

        var base = 1 - Math.pow(1 - progress, 3);
        var bump = progress < 0.8 ? 0.08 * Math.sin(progress / 0.8 * Math.PI) : 0;
        var eased = base + bump;
        var dl = FINAL_DL * eased;
        var pct = (dl / TOTAL_BYTES) * 100;

        var baseSpeed = 510100 * Math.min(progress * 2, 1);
        var jitter = 1 + (Math.random() - 0.5) * 0.1;
        var speed = baseSpeed * jitter;
        if (speed > peakSeen) peakSeen = speed;
        var peak = peakSeen;

        var remaining = TOTAL_BYTES - dl;
        var eta = speed > 100 ? Math.ceil(remaining / speed) : '--';
        var blocks = Math.round(77 * eased);
        var inflight = Math.round(15 * Math.min(progress * 3, 1));

        el('dl-title').textContent = pad(fmtBytes(dl), 7);
        el('dl-main').textContent = pad(fmtBytes(dl), 7);
        el('dl-stats').textContent = pad(fmtBytes(dl), 7);
        el('dl-bar').textContent = pad(fmtBytes(dl), 7);
        el('speed-title').textContent = pad(fmtSpeed(speed), 10);
        el('speed-main').textContent = pad(fmtSpeed(speed), 10);
        el('speed-stats').textContent = pad(fmtSpeed(speed), 10);
        el('speed-bar').textContent = pad(fmtSpeed(speed), 10);
        el('pct-main').textContent = pad(fmtPct(pct), 4);
        el('pct-bar').textContent = pad(' ' + fmtPct(pct), 5);
        el('bar').style.setProperty('--bar-fill', pct.toFixed(1) + '%');
        el('eta').textContent = pad(typeof eta === 'number' ? eta + 's' : eta, 3);
        el('blocks').textContent = pad(blocks + '/165', 7);
        el('inflight').textContent = pad(String(inflight), 3);
        el('peak').textContent = pad(fmtSpeed(peak), 8);
        el('peak-bar').textContent = pad(fmtSpeed(peak), 8);

        if (elapsed > 500) {
          el('file-status').textContent = pad('downloading', 11);
          el('file-status').className = 't-green';
          el('running').textContent = pad('1 running', 9);
        }

        conns.forEach(function (c, i) {
          if (elapsed >= c.activateAt && !c.active) {
            c.active = true;
            el('conn' + i + '-state').textContent = pad('\u2022 active', 8);
            el('conn' + i + '-state').className = 't-green';
          }
          if (c.active) {
            var connElapsed = (elapsed - c.activateAt) / 1000;
            var connProgress = Math.min(connElapsed / 5, 1);
            c.speed = c.finalSpeed * connProgress * (1 + (Math.random() - 0.5) * 0.15);
            c.bytes = c.finalBytes * connProgress;
            el('conn' + i + '-speed').textContent = pad(fmtSpeed(c.speed), 17);
            el('conn' + i + '-bytes').textContent = pad(fmtBytes(c.bytes), 15);
            el('conn' + i + '-time').textContent = pad(Math.round(connElapsed) + 's', 13);
          }
        });

        if (progress < 1) {
          requestAnimationFrame(frame);
        } else {
          setFinal();
          resolve();
        }
      }
      requestAnimationFrame(frame);
    });
  }

  if (prefersReducedMotion) {
    showAll(); setFinal();
  } else {
    (async function loop() {
      while (true) {
        resetAll();
        await sleep(400);
        await typeCommand();
        await sleep(600);
        await revealTui();
        await sleep(300);
        await simulateDownload();
        await sleep(HOLD_MS);
      }
    })();
  }
})();
