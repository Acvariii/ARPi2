import React from 'react';
import { Box, Paper, Stack, Typography } from '@mui/material';
import { useTheme } from '@mui/material/styles';
import type { Snapshot } from '../../types';

type Props = {
  snapshot: Snapshot;
  seatLabel: (seat: number) => string;
  send: (obj: unknown) => void;
  playerColors: string[];
};

export default function ExplodingKittensPanel({ snapshot, seatLabel, send, playerColors }: Props): React.ReactElement {
  if (snapshot.server_state !== 'exploding_kittens' || !snapshot.exploding_kittens) return <></>;

  const theme = useTheme();
  const ek = snapshot.exploding_kittens;

  const turnSeat = typeof ek.current_turn_seat === 'number' ? ek.current_turn_seat : null;
  const mySeat = typeof snapshot.your_player_slot === 'number' ? snapshot.your_player_slot : null;

  const panelButtons = snapshot.panel_buttons || [];
  const buttonById = new Map(panelButtons.map((b) => [b.id, b] as const));

  const ctrlDraw = buttonById.get('ek_draw');
  const ctrlNope = buttonById.get('ek_nope');
  const ctrlFavorTargets = panelButtons.filter((b) => b.id.startsWith('favor_target:'));

  const sendClick = (id: string) => send({ type: 'click_button', id });

  const cardStyle = {
    width: 74,
    aspectRatio: '5 / 7',
    borderRadius: 2,
    overflow: 'hidden',
    userSelect: 'none' as const,
  };

  const faceFromText = (text: string): { bg: string; fg: string; center: string; corner: string; ovalBorder: string } => {
    const t = String(text || '').trim().toUpperCase();

    // Treat a few control tiles like a deck-back.
    if (t === 'DRAW' || t === 'NOPE' || t.startsWith('FAVOR')) {
      return {
        bg: theme.palette.primary.main,
        fg: theme.palette.common.white,
        center: t,
        corner: t === 'DRAW' ? 'D' : t === 'NOPE' ? 'N' : 'F',
        ovalBorder: theme.palette.common.white,
      };
    }

    // EK card kinds: EK, DEF, ATK, SKIP, SHUF, FUT, FAV, NOPE
    if (t === 'EK') {
      return { bg: theme.palette.error.dark, fg: theme.palette.common.white, center: 'EK', corner: 'EK', ovalBorder: theme.palette.common.white };
    }
    if (t === 'DEF') {
      return { bg: theme.palette.success.dark, fg: theme.palette.common.white, center: 'DEFUSE', corner: 'DEF', ovalBorder: theme.palette.common.white };
    }
    if (t === 'ATK') {
      return { bg: theme.palette.warning.dark, fg: theme.palette.common.black, center: 'ATTACK', corner: 'ATK', ovalBorder: theme.palette.common.black };
    }
    if (t === 'SKIP') {
      return { bg: theme.palette.info.dark, fg: theme.palette.common.white, center: 'SKIP', corner: 'SKIP', ovalBorder: theme.palette.common.white };
    }
    if (t === 'SHUF') {
      return { bg: theme.palette.secondary.dark, fg: theme.palette.common.white, center: 'SHUFFLE', corner: 'SHUF', ovalBorder: theme.palette.common.white };
    }
    if (t === 'FUT') {
      return { bg: theme.palette.grey[800], fg: theme.palette.common.white, center: 'FUTURE', corner: 'FUT', ovalBorder: theme.palette.common.white };
    }
    if (t === 'FAV') {
      return { bg: theme.palette.primary.dark, fg: theme.palette.common.white, center: 'FAVOR', corner: 'FAV', ovalBorder: theme.palette.common.white };
    }
    if (t === 'NOPE') {
      return { bg: theme.palette.grey[900], fg: theme.palette.common.white, center: 'NOPE', corner: 'NOPE', ovalBorder: theme.palette.common.white };
    }

    return {
      bg: theme.palette.background.paper,
      fg: theme.palette.text.primary,
      center: t || '—',
      corner: t || '—',
      ovalBorder: theme.palette.divider,
    };
  };

  const renderCardTile = (opts: { key: string | number; text: string; onClick?: () => void; enabled?: boolean }) => {
    const enabled = opts.enabled ?? true;
    const clickable = !!opts.onClick && enabled && !snapshot.popup?.active;
    const face = faceFromText(opts.text);

    return (
      <Paper
        key={opts.key}
        variant="outlined"
        onClick={clickable ? opts.onClick : undefined}
        sx={{
          ...cardStyle,
          cursor: clickable ? 'pointer' : 'default',
          opacity: clickable ? 1 : 0.45,
          borderColor: clickable ? theme.palette.text.primary : 'divider',
          bgcolor: face.bg,
          color: face.fg,
          position: 'relative',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
        }}
      >
        <Box sx={{ position: 'absolute', top: 6, left: 7, lineHeight: 1 }}>
          <Typography variant="caption" sx={{ fontWeight: 800, color: face.fg }}>
            {face.corner}
          </Typography>
        </Box>
        <Box sx={{ position: 'absolute', bottom: 6, right: 7, lineHeight: 1, transform: 'rotate(180deg)' }}>
          <Typography variant="caption" sx={{ fontWeight: 800, color: face.fg }}>
            {face.corner}
          </Typography>
        </Box>

        <Box
          sx={{
            width: '76%',
            height: '58%',
            borderRadius: '999px',
            border: `2px solid ${face.ovalBorder}`,
            bgcolor: 'rgba(0,0,0,0.15)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
          }}
        >
          <Typography variant="subtitle2" sx={{ fontWeight: 900, letterSpacing: 0.3, color: face.fg, textAlign: 'center' }}>
            {face.center}
          </Typography>
        </Box>
      </Paper>
    );
  };

  const eliminatedSet = new Set((ek.eliminated_players || []).map((n) => Number(n)));
  const iAmEliminated = mySeat !== null && eliminatedSet.has(mySeat);

  return (
    <>
      <Paper variant="outlined" sx={{ p: 1.5, mb: 2 }}>
        <Stack spacing={1}>
          <Typography variant="subtitle1" align="center">
            Exploding Kittens
          </Typography>
          <Typography variant="body2" color="text.secondary" align="center">
            Deck: {ek.deck_count ?? '—'} {' · '}Discard: {ek.discard_top ?? '—'} {' · '}Draws: {ek.pending_draws ?? 1}
          </Typography>
          <Typography variant="body2" color="text.secondary" align="center">
            Turn: {turnSeat !== null ? seatLabel(turnSeat) : '—'}
          </Typography>
          {typeof ek.winner === 'number' && (
            <Typography variant="body2" sx={{ fontWeight: 700 }} align="center">
              Winner: {seatLabel(ek.winner)}
            </Typography>
          )}
          {!!ek.nope_active && (
            <Typography variant="body2" color="text.secondary" align="center">
              NOPE window active ({ek.nope_count ?? 0})
            </Typography>
          )}

          {!!ek.last_event && (
            <Typography variant="body2" sx={{ fontWeight: 700 }} align="center">
              {ek.last_event}
            </Typography>
          )}

          {iAmEliminated && (
            <Typography variant="body2" color="error" sx={{ fontWeight: 800 }} align="center">
              You exploded. You’re out.
            </Typography>
          )}
        </Stack>
      </Paper>

      {!!ek.active_players?.length && (
        <Box sx={{ mb: 2 }}>
          <Typography variant="subtitle1" gutterBottom align="center">
            Players
          </Typography>
          <Stack spacing={1} alignItems="center">
            {(ek.active_players || []).map((pidx) => {
              const eliminated = eliminatedSet.has(Number(pidx));
              return (
                <Paper
                  key={pidx}
                  variant="outlined"
                  sx={{
                    p: 1.25,
                    borderColor: playerColors[pidx % playerColors.length],
                    width: '100%',
                    maxWidth: 440,
                    textAlign: 'center',
                    opacity: eliminated ? 0.55 : 1,
                  }}
                >
                  <Typography variant="body2" sx={{ fontWeight: 700 }} align="center">
                    {seatLabel(pidx)}{eliminated ? ' (out)' : ''}
                  </Typography>
                  <Typography variant="body2" color="text.secondary" align="center">
                    Cards: {ek.hand_counts?.[String(pidx)] ?? 0}
                    {turnSeat === pidx ? ' · (turn)' : ''}
                  </Typography>
                </Paper>
              );
            })}
          </Stack>
        </Box>
      )}

      <Typography variant="subtitle1" gutterBottom align="center">
        Your Hand
      </Typography>

      {(ek.your_hand || []).length ? (
        <Paper
          variant="outlined"
          sx={{
            p: 1.25,
            mb: 2,
            borderColor: typeof mySeat === 'number' && mySeat >= 0 ? playerColors[mySeat % playerColors.length] : undefined,
          }}
        >
          <Box
            sx={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fill, minmax(74px, 74px))',
              gap: 1,
              alignItems: 'start',
              justifyContent: 'center',
            }}
          >
            {/* Prioritize any modal-ish controls (favor targets / nope / draw) before hand */}
            {!!ctrlFavorTargets.length &&
              ctrlFavorTargets.map((b) =>
                renderCardTile({
                  key: b.id,
                  text: `FAVOR ${seatLabel(Number(String(b.id).split(':')[1] || -1))}`,
                  enabled: !!b.enabled,
                  onClick: () => sendClick(b.id),
                })
              )}

            {ctrlNope &&
              renderCardTile({
                key: ctrlNope.id,
                text: 'NOPE',
                enabled: !!ctrlNope.enabled,
                onClick: () => sendClick(ctrlNope.id),
              })}

            {ctrlDraw &&
              renderCardTile({
                key: ctrlDraw.id,
                text: 'DRAW',
                enabled: !!ctrlDraw.enabled,
                onClick: () => sendClick(ctrlDraw.id),
              })}

            {(ek.your_hand || []).map((c) =>
              renderCardTile({
                key: c.idx,
                text: c.text,
                enabled: !!c.playable,
                onClick: c.playable ? () => sendClick(`ek_play:${c.idx}`) : undefined,
              })
            )}
          </Box>

          {!!ek.awaiting_favor_target && (
            <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block', textAlign: 'center' }}>
              Choose a player to Favor.
            </Typography>
          )}
        </Paper>
      ) : (
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }} align="center">
          No cards (yet).
        </Typography>
      )}
    </>
  );
}
