type CursorSnapshot = {
  player_idx: number;
  name: string;
  color?: [number, number, number];
  x: number; // 0..1
  y: number; // 0..1
  age_ms: number;
};

type Snapshot = {
  server_state: string;
  menu_games?: Array<{ key: string; label: string }>;
  player_select?: {
    slots: Array<{ player_idx: number; label: string; selected: boolean }>;
    start_enabled: boolean;
  };
  popup?: {
    active: boolean;
    popup_type?: string;
    lines?: string[];
    buttons?: Array<{ id: string; text: string; enabled: boolean }>;
  };
  panel_buttons?: Array<{ id: string; text: string; enabled: boolean }>;
  cursors?: CursorSnapshot[];
};

type SnapshotMessage = {
  type: 'snapshot';
  data: Snapshot;
};

(() => {
  const el = <T extends HTMLElement>(id: string): T => {
    const node = document.getElementById(id);
    if (!node) throw new Error(`Missing element #${id}`);
    return node as T;
  };

  const connectBtn = el<HTMLButtonElement>('connectBtn');
  const statusEl = el<HTMLDivElement>('status');
  const connectCard = el<HTMLElement>('connectCard');
  const stateCard = el<HTMLElement>('stateCard');
  const stateTitle = el<HTMLHeadingElement>('stateTitle');
  const stateBody = el<HTMLDivElement>('stateBody');
  const trackpad = el<HTMLDivElement>('trackpad');
  const escBtn = el<HTMLButtonElement>('escBtn');

  const hostInput = el<HTMLInputElement>('host');
  const playerIdxSelect = el<HTMLSelectElement>('playerIdx');
  const nameInput = el<HTMLInputElement>('name');

  let ws: WebSocket | null = null;
  let connected = false;
  let playerIdx = 0;
  let playerName = '';

  // Local trackpad cursor (immediate feedback)
  let localCursor: { x: number; y: number } | null = null;
  let lastSnapshot: Snapshot | null = null;

  function setStatus(text: string): void {
    statusEl.textContent = text;
  }

  function clamp01(v: number): number {
    if (Number.isNaN(v)) return 0;
    return Math.max(0, Math.min(1, v));
  }

  function getHost(): string {
    const v = hostInput.value.trim();
    if (v) return v;
    return window.location.hostname || 'localhost';
  }

  function send(obj: unknown): void {
    if (!ws || ws.readyState !== WebSocket.OPEN) return;
    ws.send(JSON.stringify(obj));
  }

  function sendPointerFromEvent(ev: PointerEvent, click: boolean): void {
    const r = trackpad.getBoundingClientRect();
    const x = clamp01((ev.clientX - r.left) / r.width);
    const y = clamp01((ev.clientY - r.top) / r.height);
    localCursor = { x, y };
    drawTrackpad();
    send({ type: click ? 'tap' : 'pointer', x, y, click });
  }

  function drawDot(x: number, y: number, color: string, label?: string): void {
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

  function drawTrackpad(): void {
    // Clear overlay elements
    trackpad.style.position = 'relative';
    Array.from(trackpad.querySelectorAll('.dot')).forEach((n) => n.remove());
    // Instead of class tracking, just remove all absolutely positioned div children created by us:
    // keep it simple: wipe and redraw by removing all children, but keep it empty anyway.
    // (trackpad has no children by default)
    trackpad.innerHTML = '';

    // Render snapshot cursors (everyone)
    const cursors = lastSnapshot?.cursors || [];
    for (const c of cursors) {
      const isMe = c.player_idx === playerIdx;
      const serverColor = c.color ? `rgb(${c.color[0]},${c.color[1]},${c.color[2]})` : null;
      const color = serverColor || (isMe ? '#2b7cff' : '#22c55e');
      const label = isMe ? 'You' : `P${c.player_idx + 1}`;
      drawDot(clamp01(c.x), clamp01(c.y), color, label);
    }

    // Render local cursor if no snapshot yet (or to reduce perceived lag)
    if (localCursor) {
      const alreadyHasMe = cursors.some((c) => c.player_idx === playerIdx);
      if (!alreadyHasMe) {
        drawDot(localCursor.x, localCursor.y, '#2b7cff', 'You');
      }
    }
  }

  function render(snapshot: Snapshot): void {
    stateBody.innerHTML = '';
    const serverState = snapshot?.server_state || 'unknown';
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

    // Always-available in-game panel buttons (Roll/End/Deeds/Trade/etc.)
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

  function connect(): void {
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
    ws.onmessage = (ev: MessageEvent) => {
      try {
        const msg = JSON.parse(String(ev.data)) as SnapshotMessage;
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

  // Trackpad
  trackpad.addEventListener('pointermove', (ev: PointerEvent) => {
    if (!connected) return;
    if ((ev.buttons ?? 0) === 0) {
      sendPointerFromEvent(ev, false);
    } else {
      sendPointerFromEvent(ev, true);
    }
  });
  trackpad.addEventListener('pointerdown', (ev: PointerEvent) => {
    if (!connected) return;
    trackpad.setPointerCapture?.(ev.pointerId);
    sendPointerFromEvent(ev, false);
  });
  trackpad.addEventListener('click', (ev: MouseEvent) => {
    if (!connected) return;
    // click event doesn't include pointer coords reliably; synthesize from last localCursor
    if (!localCursor) return;
    send({ type: 'tap', x: localCursor.x, y: localCursor.y, click: true });
  });

  escBtn.addEventListener('click', () => send({ type: 'esc' }));
  connectBtn.addEventListener('click', connect);

  // Initial draw
  drawTrackpad();
})();
