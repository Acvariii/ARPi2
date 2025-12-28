// NOTE: Source of truth is app.ts. This file is the runtime JS.
(() => {
  const el = (id) => {
    const node = document.getElementById(id);
    if (!node) throw new Error(`Missing element #${id}`);
    return node;
  };

  const connectBtn = el('connectBtn');
  const statusEl = el('status');
  const connectCard = el('connectCard');
  const stateCard = el('stateCard');
  const stateTitle = el('stateTitle');
  const stateBody = el('stateBody');
  const trackpad = el('trackpad');
  const escBtn = el('escBtn');

  const hostInput = el('host');
  const playerIdxSelect = el('playerIdx');
  const nameInput = el('name');

  let ws = null;
  let connected = false;
  let playerIdx = 0;
  let playerName = '';

  let localCursor = null;
  let lastSnapshot = null;

  function setStatus(text) {
    statusEl.textContent = text;
  }

  function clamp01(v) {
    if (Number.isNaN(v)) return 0;
    return Math.max(0, Math.min(1, v));
  }

  function getHost() {
    const v = hostInput.value.trim();
    if (v) return v;
    return window.location.hostname || 'localhost';
  }

  function send(obj) {
    if (!ws || ws.readyState !== WebSocket.OPEN) return;
    ws.send(JSON.stringify(obj));
  }

  function sendPointerFromEvent(ev, click) {
    const r = trackpad.getBoundingClientRect();
    const x = clamp01((ev.clientX - r.left) / r.width);
    const y = clamp01((ev.clientY - r.top) / r.height);
    localCursor = { x, y };
    drawTrackpad();
    send({ type: click ? 'tap' : 'pointer', x, y, click: !!click });
  }

  function drawDot(x, y, color, label) {
    const dot = document.createElement('div');
    dot.style.position = 'absolute';
    dot.style.left = `${x * 100}%`;
    dot.style.top = `${y * 100}%`;
    dot.style.transform = 'translate(-50%, -50%)';
    dot.style.width = '14px';
    dot.style.height = '14px';
    dot.style.borderRadius = '999px';
    dot.style.background = color;
    dot.style.border = '2px solid rgba(255,255,255,0.9)';
    dot.style.boxShadow = '0 0 0 1px rgba(0,0,0,0.35)';
    dot.style.pointerEvents = 'none';

    if (label) {
      const tag = document.createElement('div');
      tag.textContent = label;
      tag.style.position = 'absolute';
      tag.style.left = '12px';
      tag.style.top = '-10px';
      tag.style.whiteSpace = 'nowrap';
      tag.style.fontSize = '11px';
      tag.style.color = 'rgba(230,238,247,0.9)';
      tag.style.textShadow = '0 1px 2px rgba(0,0,0,0.6)';
      dot.appendChild(tag);
    }

    trackpad.appendChild(dot);
  }

  function drawTrackpad() {
    trackpad.style.position = 'relative';
    trackpad.innerHTML = '';

    const cursors = (lastSnapshot && lastSnapshot.cursors) || [];
    for (const c of cursors) {
      const isMe = c.player_idx === playerIdx;
      const serverColor = c.color ? `rgb(${c.color[0]},${c.color[1]},${c.color[2]})` : null;
      const color = serverColor || (isMe ? '#2b7cff' : '#22c55e');
      const label = isMe ? 'You' : `P${c.player_idx + 1}`;
      drawDot(clamp01(c.x), clamp01(c.y), color, label);
    }

    if (localCursor) {
      const alreadyHasMe = cursors.some((c) => c.player_idx === playerIdx);
      if (!alreadyHasMe) {
        drawDot(localCursor.x, localCursor.y, '#2b7cff', 'You');
      }
    }
  }

  function render(snapshot) {
    stateBody.innerHTML = '';
    const serverState = (snapshot && snapshot.server_state) || 'unknown';
    stateTitle.textContent = `State: ${serverState}`;

    const badge = document.createElement('div');
    badge.className = 'badge';
    badge.textContent = `You: Player ${playerIdx + 1}${playerName ? ` (${playerName})` : ''}`;
    stateBody.appendChild(badge);

    if (serverState === 'menu') {
      const st = document.createElement('div');
      st.className = 'sectionTitle';
      st.textContent = 'Choose Game';
      stateBody.appendChild(st);

      const grid = document.createElement('div');
      grid.className = 'grid';
      (snapshot.menu_games || []).forEach((g) => {
        const b = document.createElement('button');
        b.className = 'btn secondary';
        b.textContent = g.label;
        b.onclick = () => send({ type: 'select_game', key: g.key });
        grid.appendChild(b);
      });
      stateBody.appendChild(grid);
      return;
    }

    if (snapshot.player_select) {
      const st = document.createElement('div');
      st.className = 'sectionTitle';
      st.textContent = 'Player Selection';
      stateBody.appendChild(st);

      const grid = document.createElement('div');
      grid.className = 'grid';
      (snapshot.player_select.slots || []).forEach((s) => {
        const b = document.createElement('button');
        b.className = 'btn secondary';
        b.textContent = `${s.label}: ${s.selected ? 'ON' : 'OFF'}`;
        b.onclick = () => send({ type: 'set_player_selected', player_idx: s.player_idx, selected: !s.selected });
        grid.appendChild(b);
      });
      stateBody.appendChild(grid);

      const start = document.createElement('button');
      start.className = 'btn';
      start.textContent = snapshot.player_select.start_enabled ? 'Start Game' : 'Start (need more players)';
      start.disabled = !snapshot.player_select.start_enabled;
      start.onclick = () => send({ type: 'start_game' });
      stateBody.appendChild(start);
    }

    if (snapshot.panel_buttons && snapshot.panel_buttons.length) {
      const st = document.createElement('div');
      st.className = 'sectionTitle';
      st.textContent = 'Actions';
      stateBody.appendChild(st);

      const grid = document.createElement('div');
      grid.className = 'grid';
      snapshot.panel_buttons.forEach((btn) => {
        const b = document.createElement('button');
        b.className = 'btn secondary';
        b.textContent = btn.text || btn.id;
        b.disabled = !btn.enabled;
        b.onclick = () => send({ type: 'click_button', id: btn.id });
        grid.appendChild(b);
      });
      stateBody.appendChild(grid);
    }

    if (snapshot.popup && snapshot.popup.active) {
      const st = document.createElement('div');
      st.className = 'sectionTitle';
      st.textContent = 'Popup';
      stateBody.appendChild(st);

      const box = document.createElement('div');
      box.className = 'popup';

      (snapshot.popup.lines || []).forEach((ln) => {
        const p = document.createElement('div');
        p.className = 'popupLine';
        p.textContent = ln;
        box.appendChild(p);
      });
      stateBody.appendChild(box);

      const grid = document.createElement('div');
      grid.className = 'grid';
      (snapshot.popup.buttons || []).forEach((btn) => {
        const b = document.createElement('button');
        b.className = 'btn secondary';
        b.textContent = btn.text || btn.id;
        b.disabled = !btn.enabled;
        b.onclick = () => send({ type: 'click_button', id: btn.id });
        grid.appendChild(b);
      });
      stateBody.appendChild(grid);
    }
  }

  function connect() {
    playerIdx = parseInt(playerIdxSelect.value, 10) || 0;
    playerName = nameInput.value.trim();
    const host = getHost();
    const url = `ws://${host}:8765/ui`;
    setStatus(`Connecting to ${url} ...`);

    ws = new WebSocket(url);
    ws.onopen = () => {
      connected = true;
      setStatus('Connected');
      connectCard.hidden = true;
      stateCard.hidden = false;
      send({ type: 'hello', player_idx: playerIdx, name: playerName });
    };
    ws.onclose = () => {
      connected = false;
      lastSnapshot = null;
      drawTrackpad();
      setStatus('Disconnected');
      connectCard.hidden = false;
      stateCard.hidden = true;
    };
    ws.onerror = () => {
      setStatus('WebSocket error (check IP/firewall)');
    };
    ws.onmessage = (ev) => {
      try {
        const msg = JSON.parse(String(ev.data));
        if (msg.type === 'snapshot') {
          lastSnapshot = msg.data;
          drawTrackpad();
          render(msg.data);
        }
      } catch {
        // ignore
      }
    };
  }

  trackpad.addEventListener('pointermove', (ev) => {
    if (!connected) return;
    if ((ev.buttons || 0) === 0) {
      sendPointerFromEvent(ev, false);
    } else {
      sendPointerFromEvent(ev, true);
    }
  });
  trackpad.addEventListener('pointerdown', (ev) => {
    if (!connected) return;
    if (trackpad.setPointerCapture) trackpad.setPointerCapture(ev.pointerId);
    sendPointerFromEvent(ev, false);
  });
  trackpad.addEventListener('click', () => {
    if (!connected) return;
    if (!localCursor) return;
    send({ type: 'tap', x: localCursor.x, y: localCursor.y, click: true });
  });

  escBtn.addEventListener('click', () => send({ type: 'esc' }));
  connectBtn.addEventListener('click', connect);

  drawTrackpad();
})();
