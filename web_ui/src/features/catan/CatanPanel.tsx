import React, { useCallback, useMemo, useRef } from 'react';
import { Box, Button, Paper, Stack, Typography } from '@mui/material';
import type { Snapshot } from '../../types';

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
  const buttonById = useMemo(() => new Map(buttons.map((b) => [b.id, b] as const)), [buttons]);

  const rollBtn = buttonById.get('roll');
  const endBtn = buttonById.get('end_turn');

  const sendClick = (id: string) => send({ type: 'click_button', id });

  const padRef = useRef<HTMLDivElement | null>(null);

  const sendPointer = useCallback(
    (clientX: number, clientY: number, click: boolean) => {
      const el = padRef.current;
      if (!el) return;
      const rect = el.getBoundingClientRect();
      const x = (clientX - rect.left) / Math.max(1, rect.width);
      const y = (clientY - rect.top) / Math.max(1, rect.height);
      const nx = Math.max(0, Math.min(1, x));
      const ny = Math.max(0, Math.min(1, y));
      send({ type: click ? 'tap' : 'pointer', x: nx, y: ny, click });
    },
    [send]
  );

  return (
    <Stack spacing={1.25}>
      <Paper variant="outlined" sx={{ p: 1.25 }}>
        <Typography variant="h6" align="center">
          Catan
        </Typography>
        <Typography variant="body2" color="text.secondary" align="center">
          Turn: {typeof turnSeat === 'number' ? seatLabel(turnSeat) : '—'} · Expansion: {st.expansion_mode || '—'}
        </Typography>
        <Typography variant="caption" color="text.secondary" display="block" align="center" sx={{ mt: 0.25 }}>
          {isMyTurn ? 'Your turn' : 'Waiting'} · Phase: {st.phase || '—'} · Rolled: {st.rolled ? 'yes' : 'no'}
        </Typography>
        {st.your_resources ? (
          <Typography variant="caption" color="text.secondary" display="block" align="center" sx={{ mt: 0.25 }}>
            Resources: 🌲 {st.your_resources.wood ?? 0} · 🧱 {st.your_resources.brick ?? 0} · 🐑 {st.your_resources.sheep ?? 0} · 🌾{' '}
            {st.your_resources.wheat ?? 0} · ⛰️ {st.your_resources.ore ?? 0}
          </Typography>
        ) : null}
        {st.last_event ? (
          <Typography variant="caption" color="text.secondary" display="block" align="center" sx={{ mt: 0.5 }}>
            {st.last_event}
          </Typography>
        ) : null}
      </Paper>

      <Paper variant="outlined" sx={{ p: 1.25 }}>
        <Typography variant="subtitle1" gutterBottom>
          Actions
        </Typography>
        <Stack direction="row" spacing={1} sx={{ mb: 1 }}>
          <Button variant="contained" onClick={() => sendClick('roll')} disabled={!rollBtn?.enabled || !isMyTurn || !!snapshot.popup?.active}>
            Roll Dice
          </Button>
          <Button variant="outlined" onClick={() => sendClick('end_turn')} disabled={!endBtn?.enabled || !isMyTurn || !!snapshot.popup?.active}>
            End Turn
          </Button>
        </Stack>

        {buttons.length > 0 ? (
          <Box
            sx={{
              display: 'grid',
              gridTemplateColumns: { xs: 'repeat(2, 1fr)', sm: 'repeat(3, 1fr)' },
              gap: 1,
            }}
          >
            {buttons.map((b) => (
              <Button
                key={b.id}
                variant={b.id === 'roll' ? 'contained' : 'outlined'}
                onClick={() => sendClick(b.id)}
                disabled={!b.enabled || !!snapshot.popup?.active || (b.id === 'roll' && !isMyTurn) || (b.id === 'end_turn' && !isMyTurn)}
                sx={{ minHeight: { xs: 52, sm: 44 }, fontSize: { xs: 15, sm: 14 } }}
              >
                {b.text}
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
        <Box
          ref={padRef}
          onPointerMove={(e) => sendPointer(e.clientX, e.clientY, false)}
          onPointerDown={(e) => {
            if (snapshot.popup?.active) return;
            try {
              (e.currentTarget as any).setPointerCapture?.(e.pointerId);
            } catch {
              // ignore
            }
            sendPointer(e.clientX, e.clientY, true);
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
            Tap here to place/select on the board
          </Typography>
        </Box>
      </Paper>
    </Stack>
  );
}
