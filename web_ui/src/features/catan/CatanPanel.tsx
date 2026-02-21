import React, { useCallback, useMemo, useRef } from 'react';
import { Box, Button, Chip, Paper, Stack, Typography } from '@mui/material';
import type { Snapshot } from '../../types';
import GameBanner from '../../components/GameBanner';

export default function CatanPanel(props: {
  snapshot: Snapshot;
  send: (obj: unknown) => void;
  seatLabel: (seat: number) => string;
}): React.ReactElement {
  const { snapshot, send, seatLabel } = props;
  const st = snapshot.catan;

  if (snapshot.server_state !== 'catan' || !st) return <></>;

  const mySeat = typeof snapshot.your_player_slot === 'number' ? snapshot.your_player_slot : null;
  const turnSeat = typeof st.current_turn_seat === 'number' ? st.current_turn_seat : null;
  const isMyTurn = typeof mySeat === 'number' && typeof turnSeat === 'number' && mySeat === turnSeat;

  const buttons = snapshot.panel_buttons || [];

  // Some games include Roll/End in panel_buttons; avoid showing multiple sets
  // by rendering actions in a single unified grid.

  const buttonEmoji = useCallback((id: string): string => {
    if (id === 'roll') return '🎲';
    if (id === 'end_turn') return '✅';
    if (id === 'build_road') return '🛣️';
    if (id === 'build_settlement') return '🏠';
    if (id === 'build_city') return '🏰';
    if (id === 'buy_dev') return '🃏';
    if (id === 'trade_bank') return '🏦';
    if (id === 'trade_player') return '🤝';
    if (id === 'trade_confirm') return '🤝';
    if (id === 'trade_cancel') return '↩️';
    if (id.startsWith('trade_give:') || id.startsWith('trade_get:')) return '🔁';
    if (id.startsWith('trade_to:')) return '👥';
    if (id.startsWith('p2p_give:') || id.startsWith('p2p_get:')) return '🔁';
    if (id === 'p2p_offer') return '📨';
    if (id === 'p2p_accept') return '✅';
    if (id === 'p2p_decline') return '❌';
    if (id.startsWith('play_dev:knight')) return '🦹';
    if (id.startsWith('play_dev:road_building')) return '🛣️';
    if (id.startsWith('play_dev:year_of_plenty')) return '🌾';
    if (id.startsWith('play_dev:monopoly')) return '💰';
    if (id.startsWith('discard:')) return '🗑️';
    if (id.startsWith('steal:')) return '🧤';
    if (id === 'skip_steal') return '⏭️';
    if (id === 'cancel_build') return '❌';
    return '✨';
  }, []);

  const buttonLabel = useCallback(
    (id: string, text: string): string => {
      const e = buttonEmoji(id);
      return `${e} ${text}`;
    },
    [buttonEmoji]
  );

  const sendClick = (id: string) => send({ type: 'click_button', id });

  const padRef = useRef<HTMLDivElement | null>(null);

  // Mobile/desktop input behavior:
  // - Coarse pointer (phones/tablets): drag to move the cursor; "Select" taps at last cursor location.
  // - Fine pointer (mouse): click directly on the pad to tap at that point; moving the mouse updates cursor.
  const isCoarsePointer = useMemo(() => {
    try {
      if (typeof window !== 'undefined' && typeof window.matchMedia === 'function') {
        return window.matchMedia('(pointer: coarse)').matches;
      }
    } catch {
      // ignore
    }
    try {
      return typeof navigator !== 'undefined' && (navigator as any).maxTouchPoints > 0;
    } catch {
      return false;
    }
  }, []);

  const lastCursorRef = useRef<{ x: number; y: number }>({ x: 0.5, y: 0.5 });
  const draggingRef = useRef<boolean>(false);

  const toPadCoords = useCallback((clientX: number, clientY: number) => {
    const el = padRef.current;
    if (!el) return null;
    const rect = el.getBoundingClientRect();
    const x = (clientX - rect.left) / Math.max(1, rect.width);
    const y = (clientY - rect.top) / Math.max(1, rect.height);
    const nx = Math.max(0, Math.min(1, x));
    const ny = Math.max(0, Math.min(1, y));
    return { x: nx, y: ny };
  }, []);

  const sendPointer = useCallback(
    (clientX: number, clientY: number) => {
      const p = toPadCoords(clientX, clientY);
      if (!p) return;
      lastCursorRef.current = p;
      send({ type: 'pointer', x: p.x, y: p.y, click: false });
    },
    [send, toPadCoords]
  );

  const sendTapAtLastCursor = useCallback(() => {
    const p = lastCursorRef.current || { x: 0.5, y: 0.5 };
    send({ type: 'tap', x: p.x, y: p.y, click: true });
  }, [send]);

  const sendTapAtPoint = useCallback(
    (clientX: number, clientY: number) => {
      const el = padRef.current;
      if (!el) return;
      const p = toPadCoords(clientX, clientY);
      if (!p) return;
      // Desktop behavior: click where you press.
      lastCursorRef.current = p;
      send({ type: 'tap', x: p.x, y: p.y, click: true });
    },
    [send, toPadCoords]
  );

  return (
    <Stack spacing={1.25} sx={{ animation: 'fadeInUp 0.4s ease-out' }}>
      <GameBanner game="catan" />
      <Paper variant="outlined" sx={{ p: 1.25 }}>
        <Stack direction="row" spacing={1} justifyContent="center" flexWrap="wrap" useFlexGap sx={{ mb: 0.75 }}>
          <Typography variant="body2" color="text.secondary">
            Turn: {typeof turnSeat === 'number' ? seatLabel(turnSeat) : '—'}
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Phase: {st.phase || '—'}
          </Typography>
          {typeof st.last_roll === 'number' && (
            <Chip
              label={`🎲 ${st.last_roll}`}
              size="small"
              sx={{
                bgcolor: st.last_roll === 7 ? '#c62828' : '#1565c0',
                color: '#fff',
                fontWeight: 900,
                fontSize: '0.85rem',
                height: 24,
                animation: st.last_roll === 7 ? 'blink 0.6s ease-in-out 3' : 'badgePop 0.35s ease-out',
              }}
            />
          )}
        </Stack>
        {/* VP + badges */}
        <Stack direction="row" spacing={1} justifyContent="center" flexWrap="wrap" useFlexGap sx={{ mb: 0.75 }}>
          {typeof st.vp === 'number' && (
            <Chip label={`⭐ ${st.vp} VP`} size="small" sx={{ bgcolor: '#f9a825', color: '#000', fontWeight: 900, height: 22, animation: 'badgePop 0.35s ease-out' }} />
          )}
          {typeof st.knights_played === 'number' && st.knights_played > 0 && (
            <Chip label={`⚔️ ${st.knights_played} Knight${st.knights_played !== 1 ? 's' : ''}`} size="small" variant="outlined" sx={{ animation: 'badgePop 0.35s ease-out' }} />
          )}
          {typeof st.largest_army_holder === 'number' && st.largest_army_holder === mySeat && (
            <Chip label="⚔️ Largest Army" size="small" sx={{ bgcolor: '#7b1fa2', color: '#fff', fontWeight: 700, height: 22, animation: 'winnerShimmer 2s linear infinite' }} />
          )}
          {typeof st.longest_road_holder === 'number' && st.longest_road_holder === mySeat && (
            <Chip label="🛣️ Longest Road" size="small" sx={{ bgcolor: '#1565c0', color: '#fff', fontWeight: 700, height: 22, animation: 'winnerShimmer 2s linear infinite' }} />
          )}
        </Stack>
        {st.your_resources ? (
          <Stack direction="row" spacing={0.75} justifyContent="center" flexWrap="wrap" useFlexGap>
            {([
              ['wood', '🌲', '#2e7d32', '#fff'],
              ['brick', '🧱', '#bf360c', '#fff'],
              ['sheep', '🐑', '#558b2f', '#fff'],
              ['wheat', '🌾', '#f9a825', '#000'],
              ['ore', '⛰️', '#546e7a', '#fff'],
            ] as [string, string, string, string][]).map(([res, em, bg, fg], i) => (
              <Chip
                key={res}
                label={`${em} ${st.your_resources![res] ?? 0}`}
                size="small"
                sx={{ bgcolor: bg, color: fg, fontWeight: 700, fontSize: '0.8rem', height: 24, minWidth: 44, animation: `badgePop 0.3s ease-out ${i * 0.05}s both` }}
              />
            ))}
          </Stack>
        ) : null}
        {st.last_event ? (
          <Typography variant="caption" color="text.secondary" display="block" align="center" sx={{ mt: 0.5, animation: 'slideInRight 0.4s ease-out' }}>
            {st.last_event}
          </Typography>
        ) : null}
      </Paper>

      <Paper variant="outlined" sx={{ p: 1.25 }}>
        <Typography variant="subtitle1" gutterBottom>
          Actions
        </Typography>
        {buttons.length > 0 ? (
          <Box
            sx={{
              display: 'grid',
              gridTemplateColumns: { xs: 'repeat(2, 1fr)', sm: 'repeat(3, 1fr)' },
              gap: 1,
            }}
          >
            {buttons.map((b, bIdx) => (
              <Button
                key={b.id}
                variant={b.id === 'roll' ? 'contained' : b.id === 'end_turn' ? 'outlined' : 'outlined'}
                onClick={() => sendClick(b.id)}
                disabled={!b.enabled || !!snapshot.popup?.active || (b.id === 'roll' && !isMyTurn) || (b.id === 'end_turn' && !isMyTurn)}
                sx={{
                  minHeight: { xs: 52, sm: 44 },
                  fontSize: { xs: 15, sm: 14 },
                  gridColumn: b.id === 'roll' || b.id === 'end_turn' ? { xs: 'span 2', sm: 'span 3' } : undefined,
                  animation: `bounceIn 0.4s ease-out ${bIdx * 0.05}s both`,
                }}
              >
                {buttonLabel(b.id, b.text)}
              </Button>
            ))}
          </Box>
        ) : (
          <Typography variant="body2" color="text.secondary">
            No actions available.
          </Typography>
        )}
        {typeof st.last_roll === 'number' ? (
          <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
            Last roll: {st.last_roll}
          </Typography>
        ) : null}
      </Paper>

      <Paper variant="outlined" sx={{ p: 1.25 }}>
        <Typography variant="subtitle1" gutterBottom>
          Map
        </Typography>
        <Typography variant="body2" color="text.secondary">
          Tiles: {Array.isArray(st.tiles) ? st.tiles.length : 0} (see wall display)
        </Typography>
        <Typography variant="body2" color="text.secondary">
          Ports: {Array.isArray((st as any).ports) ? ((st as any).ports as any[]).length : 0}
        </Typography>
        {isCoarsePointer ? (
          <Stack direction="row" spacing={1} sx={{ mt: 1 }}>
            <Button
              variant="contained"
              onClick={sendTapAtLastCursor}
              disabled={!!snapshot.popup?.active}
              sx={{ minHeight: 44, flex: 1 }}
            >
              Select (tap)
            </Button>
          </Stack>
        ) : null}
        <Box
          ref={padRef}
          onPointerMove={(e) => {
            if (snapshot.popup?.active) return;
            if (isCoarsePointer && !draggingRef.current) return;
            sendPointer(e.clientX, e.clientY);
          }}
          onPointerDown={(e) => {
            if (snapshot.popup?.active) return;
            try {
              (e.currentTarget as any).setPointerCapture?.(e.pointerId);
            } catch {
              // ignore
            }
            if (isCoarsePointer) {
              // Mobile: do NOT reposition the cursor on tap-down.
              // Dragging will move it; selection is via the Select button.
              draggingRef.current = true;
              return;
            }
            // Desktop: click at the point pressed.
            sendTapAtPoint(e.clientX, e.clientY);
          }}
          onPointerUp={() => {
            draggingRef.current = false;
          }}
          onPointerCancel={() => {
            draggingRef.current = false;
          }}
          sx={{
            mt: 1,
            height: { xs: 240, sm: 180 },
            borderRadius: 1,
            border: '1px solid',
            borderColor: 'divider',
            bgcolor: 'background.paper',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            userSelect: 'none',
            touchAction: 'none',
          }}
        >
          <Typography variant="body2" color="text.secondary" align="center" sx={{ px: 2 }}>
            {isCoarsePointer
              ? 'Drag here to move the cursor. Use Select to tap.'
              : 'Move/click here to tap on the board.'}
            <br />
            Settlements go on intersections (not hex centers).
          </Typography>
        </Box>

      </Paper>

      <Paper variant="outlined" sx={{ p: 1.25 }}>
        <Typography variant="subtitle1" gutterBottom>
          Prices
        </Typography>
        <Typography variant="body2" color="text.secondary">
          🛣️ Road: 🌲 1 + 🧱 1
        </Typography>
        <Typography variant="body2" color="text.secondary">
          🏠 Settlement: 🌲 1 + 🧱 1 + 🐑 1 + 🌾 1
        </Typography>
        <Typography variant="body2" color="text.secondary">
          🏰 City: ⛰️ 3 + 🌾 2
        </Typography>
        <Typography variant="body2" color="text.secondary">
          🃏 Dev Card: 🐑 1 + 🌾 1 + ⛰️ 1
        </Typography>
      </Paper>
    </Stack>
  );
}
