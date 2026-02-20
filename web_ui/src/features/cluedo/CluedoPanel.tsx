import React, { useEffect, useMemo, useRef, useState } from 'react';
import { Box, Paper, Stack, TextField, Typography } from '@mui/material';
import { useTheme } from '@mui/material/styles';
import type { Snapshot } from '../../types';
import GameBanner from '../../components/GameBanner';

type Props = {
  snapshot: Snapshot;
  seatLabel: (seat: number) => string;
  send: (obj: unknown) => void;
  playerColors: string[];
};

export default function CluedoPanel({ snapshot, seatLabel, send, playerColors }: Props): React.ReactElement {
  if (snapshot.server_state !== 'cluedo' || !snapshot.cluedo) return <></>;

  const theme = useTheme();
  const cl = snapshot.cluedo;

  const mySeat = typeof snapshot.your_player_slot === 'number' ? snapshot.your_player_slot : null;
  const turnSeat = typeof cl.current_turn_seat === 'number' ? cl.current_turn_seat : null;
  const dice = Array.isArray(cl.dice) && cl.dice.length === 2 ? (cl.dice as [number, number]) : null;

  const panelButtons = snapshot.panel_buttons || [];
  const buttonById = useMemo(() => new Map(panelButtons.map((b) => [b.id, b] as const)), [panelButtons]);

  const sendClick = (id: string) => send({ type: 'click_button', id });

  const canInteract = !snapshot.popup?.active && typeof mySeat === 'number' && mySeat >= 0;

  const sectionBorderColor =
    typeof mySeat === 'number' && mySeat >= 0 ? playerColors[mySeat % playerColors.length] : undefined;

  const rollBtn = buttonById.get('roll');
  const envelopeBtn = buttonById.get('envelope');
  const suggestBtn = buttonById.get('suggest');
  const accuseBtn = buttonById.get('accuse');
  const endTurnBtn = buttonById.get('end_turn');

  const moveUp = buttonById.get('move:up');
  const moveDown = buttonById.get('move:down');
  const moveLeft = buttonById.get('move:left');
  const moveRight = buttonById.get('move:right');

  const pickSuspects = panelButtons.filter((b) => b.id.startsWith('pick_suspect:'));
  const pickWeapons = panelButtons.filter((b) => b.id.startsWith('pick_weapon:'));
  const pickRooms = panelButtons.filter((b) => b.id.startsWith('pick_room:'));
  const revealButtons = panelButtons.filter((b) => b.id.startsWith('reveal:'));

  const [notes, setNotes] = useState('');
  const gameKey = typeof cl.game_id === 'number' ? cl.game_id : null;
  const lastGameKeyRef = useRef<number | null>(gameKey);

  useEffect(() => {
    if (gameKey === null) return;
    if (lastGameKeyRef.current === null) {
      lastGameKeyRef.current = gameKey;
      return;
    }
    if (lastGameKeyRef.current !== gameKey) {
      lastGameKeyRef.current = gameKey;
      setNotes('');
    }
  }, [gameKey]);

  const padButtonSx = (enabled: boolean) => ({
    p: 1,
    borderRadius: 2,
    cursor: enabled ? 'pointer' : 'default',
    opacity: enabled ? 1 : 0.45,
    borderColor: enabled ? theme.palette.text.primary : 'divider',
    textAlign: 'center',
    userSelect: 'none' as const,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    minHeight: 64,
  });

  const renderPadButton = (opts: { id: string; label: string; enabled: boolean }) => (
    <Paper
      key={opts.id}
      variant="outlined"
      onClick={opts.enabled ? () => sendClick(opts.id) : undefined}
      sx={padButtonSx(opts.enabled)}
    >
      <Typography variant="body2" sx={{ fontWeight: 900 }}>
        {opts.label}
      </Typography>
    </Paper>
  );

  return (
    <>
      <GameBanner game="cluedo" />
      <Paper variant="outlined" sx={{ p: 1.5, mb: 2 }}>
        <Stack spacing={0.75}>
          <Typography variant="body2" color="text.secondary" align="center">
            Turn: {turnSeat !== null ? seatLabel(turnSeat) : '—'}
            {dice ? ` · Roll: ${dice[0]}+${dice[1]}=${typeof cl.last_roll === 'number' ? cl.last_roll : dice[0] + dice[1]}` : ''}
            {!dice && typeof cl.last_roll === 'number' ? ` · Roll: ${cl.last_roll}` : ''}
            {typeof cl.steps_remaining === 'number' ? ` · Steps: ${cl.steps_remaining}` : ''}
          </Typography>
          {!!cl.last_event && (
            <Typography variant="body2" sx={{ fontWeight: 700 }} align="center">
              {cl.last_event}
            </Typography>
          )}
          {!!cl.private_event && (
            <Typography variant="caption" color="text.secondary" align="center">
              {cl.private_event}
            </Typography>
          )}
          {typeof cl.winner === 'number' && (
            <Typography variant="body2" sx={{ fontWeight: 800 }} align="center">
              Winner: {seatLabel(cl.winner)}
            </Typography>
          )}
        </Stack>
      </Paper>

      {!!cl.private_event && String(cl.private_event).startsWith('Case File:') && (
        <Paper variant="outlined" sx={{ p: 1.25, mb: 2, borderColor: sectionBorderColor }}>
          <Stack spacing={0.5}>
            <Typography variant="subtitle2" align="center" sx={{ fontWeight: 900 }}>
              Envelope (Case File)
            </Typography>
            <Typography variant="body2" align="center" sx={{ fontWeight: 800 }}>
              {cl.private_event}
            </Typography>
          </Stack>
        </Paper>
      )}

      <Typography variant="subtitle1" gutterBottom align="center">
        Your Hand
      </Typography>
      {(cl.your_hand || []).length ? (
        <Paper variant="outlined" sx={{ p: 1.25, mb: 2, borderColor: sectionBorderColor }}>
          <Box
            sx={{
              display: 'grid',
              gridTemplateColumns: {
                xs: 'repeat(auto-fill, minmax(120px, 1fr))',
                sm: 'repeat(auto-fill, minmax(150px, 150px))',
              },
              gap: { xs: 0.75, sm: 1 },
              justifyContent: 'center',
            }}
          >
            {(cl.your_hand || []).map((c, idx) => (
              <Paper
                key={`${c.kind}:${c.name}:${idx}`}
                variant="outlined"
                sx={{
                  p: { xs: 0.75, sm: 1 },
                  borderRadius: 2,
                  bgcolor: theme.palette.background.paper,
                }}
              >
                <Typography variant="body2" sx={{ fontWeight: 800, fontSize: { xs: '0.78rem', sm: '0.875rem' } }}>
                  {c.text}
                </Typography>
                <Typography variant="caption" color="text.secondary" sx={{ fontSize: { xs: '0.65rem', sm: '0.75rem' } }}>
                  {String(c.kind || '').toUpperCase()}
                </Typography>
              </Paper>
            ))}
          </Box>
        </Paper>
      ) : (
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }} align="center">
          No cards (yet).
        </Typography>
      )}

      {canInteract &&
        !snapshot.popup?.active &&
        (envelopeBtn || rollBtn || suggestBtn || accuseBtn || endTurnBtn || moveUp || moveDown || moveLeft || moveRight || pickSuspects.length || pickWeapons.length || pickRooms.length || revealButtons.length) && (
          <>
            <Typography variant="subtitle1" gutterBottom align="center">
              Actions
            </Typography>

            <Paper variant="outlined" sx={{ p: 1.25, mb: 1.5, borderColor: sectionBorderColor }}>
              <Box
                sx={{
                  display: 'grid',
                  gridTemplateColumns: 'repeat(3, minmax(0, 120px))',
                  gap: 1,
                  justifyContent: 'center',
                }}
              >
                {/* Row 1 */}
                {rollBtn
                  ? renderPadButton({ id: 'roll', label: rollBtn.text, enabled: !!rollBtn.enabled })
                  : <Box />}
                {moveUp
                  ? renderPadButton({ id: 'move:up', label: moveUp.text, enabled: !!moveUp.enabled })
                  : <Box />}
                {envelopeBtn
                  ? renderPadButton({ id: 'envelope', label: envelopeBtn.text, enabled: !!envelopeBtn.enabled })
                  : <Box />}

                {/* Row 2 */}
                {moveLeft
                  ? renderPadButton({ id: 'move:left', label: moveLeft.text, enabled: !!moveLeft.enabled })
                  : <Box />}
                {endTurnBtn
                  ? renderPadButton({ id: 'end_turn', label: endTurnBtn.text, enabled: !!endTurnBtn.enabled })
                  : <Box />}
                {moveRight
                  ? renderPadButton({ id: 'move:right', label: moveRight.text, enabled: !!moveRight.enabled })
                  : <Box />}

                {/* Row 3 */}
                {accuseBtn
                  ? renderPadButton({ id: 'accuse', label: accuseBtn.text, enabled: !!accuseBtn.enabled })
                  : <Box />}
                {moveDown
                  ? renderPadButton({ id: 'move:down', label: moveDown.text, enabled: !!moveDown.enabled })
                  : <Box />}
                {suggestBtn
                  ? renderPadButton({ id: 'suggest', label: suggestBtn.text, enabled: !!suggestBtn.enabled })
                  : <Box />}
              </Box>
            </Paper>

            {(pickSuspects.length > 0 || pickWeapons.length > 0 || pickRooms.length > 0 || revealButtons.length > 0) && (
              <Paper variant="outlined" sx={{ p: 1.25, mb: 2, borderColor: sectionBorderColor }}>
                <Box
                  sx={{
                    display: 'grid',
                    gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 180px))',
                    gap: 1,
                    justifyContent: 'center',
                  }}
                >
                  {revealButtons.map((b) => (
                    <Paper
                      key={b.id}
                      variant="outlined"
                      onClick={b.enabled ? () => sendClick(b.id) : undefined}
                      sx={padButtonSx(!!b.enabled)}
                    >
                      <Typography variant="body2" sx={{ fontWeight: 900 }}>
                        {b.text}
                      </Typography>
                    </Paper>
                  ))}
                  {pickSuspects.map((b) => (
                    <Paper
                      key={b.id}
                      variant="outlined"
                      onClick={b.enabled ? () => sendClick(b.id) : undefined}
                      sx={padButtonSx(!!b.enabled)}
                    >
                      <Typography variant="body2" sx={{ fontWeight: 900 }}>
                        {b.text}
                      </Typography>
                    </Paper>
                  ))}
                  {pickWeapons.map((b) => (
                    <Paper
                      key={b.id}
                      variant="outlined"
                      onClick={b.enabled ? () => sendClick(b.id) : undefined}
                      sx={padButtonSx(!!b.enabled)}
                    >
                      <Typography variant="body2" sx={{ fontWeight: 900 }}>
                        {b.text}
                      </Typography>
                    </Paper>
                  ))}
                  {pickRooms.map((b) => (
                    <Paper
                      key={b.id}
                      variant="outlined"
                      onClick={b.enabled ? () => sendClick(b.id) : undefined}
                      sx={padButtonSx(!!b.enabled)}
                    >
                      <Typography variant="body2" sx={{ fontWeight: 900 }}>
                        {b.text}
                      </Typography>
                    </Paper>
                  ))}
                </Box>
              </Paper>
            )}
          </>
        )}

      <Typography variant="subtitle1" gutterBottom align="center">
        Notes
      </Typography>
      <Paper variant="outlined" sx={{ p: 1.25, mb: 2, borderColor: sectionBorderColor }}>
        <TextField
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          placeholder="Type your notes here…"
          multiline
          minRows={6}
          fullWidth
        />
      </Paper>

      <Typography variant="subtitle1" gutterBottom align="center">
        Players
      </Typography>
      <Paper variant="outlined" sx={{ p: 1.25, mb: 2 }}>
        <Stack spacing={0.5}>
          {(cl.players || []).map((p) => (
            <Paper
              key={p.seat}
              variant="outlined"
              sx={{
                p: 1,
                borderColor: playerColors[p.seat % playerColors.length],
                opacity: p.eliminated ? 0.6 : 1,
              }}
            >
              <Stack direction="row" spacing={1} alignItems="center" justifyContent="space-between">
                <Typography variant="body2" sx={{ fontWeight: 800 }}>
                  {p.name}
                  {turnSeat === p.seat ? ' (Turn)' : ''}
                  {p.eliminated ? ' (Out)' : ''}
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  {p.room || '—'} · {p.hand_count} cards
                </Typography>
              </Stack>
            </Paper>
          ))}
        </Stack>
      </Paper>
    </>
  );
}
