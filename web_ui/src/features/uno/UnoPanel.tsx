import React from 'react';
import { Box, Button, Paper, Stack, Typography } from '@mui/material';
import { useTheme } from '@mui/material/styles';
import type { Snapshot } from '../../types';

type Props = {
  snapshot: Snapshot;
  seatLabel: (seat: number) => string;
  send: (obj: unknown) => void;
  playerColors: string[];
};

export default function UnoPanel({ snapshot, seatLabel, send, playerColors }: Props): React.ReactElement {
  if (snapshot.server_state !== 'uno' || !snapshot.uno) return <></>;

  const theme = useTheme();
  const uno = snapshot.uno;
  const turnSeat = typeof uno.current_turn_seat === 'number' ? uno.current_turn_seat : null;
  const mySeat = typeof snapshot.your_player_slot === 'number' ? snapshot.your_player_slot : null;

  const panelButtons = snapshot.panel_buttons || [];
  const buttonById = new Map(panelButtons.map((b) => [b.id, b] as const));

  const ctrlDraw = buttonById.get('draw');
  const ctrlEnd = buttonById.get('end');
  const ctrlPlayAgain = buttonById.get('play_again');
  const ctrlForceStart = buttonById.get('force_start');
  const ctrlColors = ['R', 'G', 'B', 'Y']
    .map((c) => buttonById.get(`color:${c}`))
    .filter((b): b is NonNullable<typeof b> => !!b);

  const sendClick = (id: string) => send({ type: 'click_button', id });

  const cardStyle = {
    width: 74,
    aspectRatio: '5 / 7',
    borderRadius: 2,
    overflow: 'hidden',
    userSelect: 'none' as const,
  };

  const faceFromText = (text: string): { bg: string; fg: string; center: string; corner: string } => {
    const t = String(text || '').trim().toUpperCase();

    if (t.startsWith('WILD')) {
      return {
        bg: theme.palette.grey[800],
        fg: theme.palette.common.white,
        center: t.replace('WILD', 'WILD').replace('+4', '+4'),
        corner: t.includes('+4') ? '+4' : 'W',
      };
    }

    const c = t[0];
    const rest = t.slice(1);
    if (c === 'R') return { bg: theme.palette.error.main, fg: theme.palette.common.white, center: rest || 'R', corner: rest || 'R' };
    if (c === 'G') return { bg: theme.palette.success.main, fg: theme.palette.common.white, center: rest || 'G', corner: rest || 'G' };
    if (c === 'B') return { bg: theme.palette.info.main, fg: theme.palette.common.white, center: rest || 'B', corner: rest || 'B' };
    if (c === 'Y') return { bg: theme.palette.warning.main, fg: theme.palette.common.black, center: rest || 'Y', corner: rest || 'Y' };

    return {
      bg: theme.palette.background.paper,
      fg: theme.palette.text.primary,
      center: t || '—',
      corner: t || '—',
    };
  };

  const renderCardTile = (opts: {
    key: string | number;
    text: string;
    onClick?: () => void;
    enabled?: boolean;
    asBack?: boolean;
  }) => {
    const enabled = opts.enabled ?? true;
    const clickable = !!opts.onClick && enabled && !snapshot.popup?.active;
    const face = faceFromText(opts.text);

    // Card back: neutral look (like the deck)
    const bg = opts.asBack ? theme.palette.primary.main : face.bg;
    const fg = opts.asBack ? theme.palette.common.white : face.fg;

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
          bgcolor: bg,
          color: fg,
          position: 'relative',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
        }}
      >
        {/* corner labels */}
        <Box sx={{ position: 'absolute', top: 6, left: 7, lineHeight: 1 }}>
          <Typography variant="caption" sx={{ fontWeight: 800, color: fg }}>
            {opts.asBack ? 'UNO' : face.corner}
          </Typography>
        </Box>
        <Box sx={{ position: 'absolute', bottom: 6, right: 7, lineHeight: 1, transform: 'rotate(180deg)' }}>
          <Typography variant="caption" sx={{ fontWeight: 800, color: fg }}>
            {opts.asBack ? 'UNO' : face.corner}
          </Typography>
        </Box>

        {/* center oval */}
        <Box
          sx={{
            width: '76%',
            height: '58%',
            borderRadius: '999px',
            border: `2px solid ${theme.palette.common.white}`,
            bgcolor: 'rgba(0,0,0,0.15)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
          }}
        >
          <Typography variant="subtitle1" sx={{ fontWeight: 900, letterSpacing: 0.5, color: fg }}>
            {opts.asBack ? opts.text : face.center}
          </Typography>
        </Box>
      </Paper>
    );
  };

  return (
    <>
      <Paper variant="outlined" sx={{ p: 1.5, mb: 2 }}>
        <Stack spacing={1}>
          <Typography variant="subtitle1" align="center">
            Uno
          </Typography>
          <Typography variant="body2" color="text.secondary" align="center">
            Top: {uno.top_card ?? '—'} {' · '}Color: {uno.current_color ?? '—'}
          </Typography>
          <Typography variant="body2" color="text.secondary" align="center">
            Turn: {turnSeat !== null ? seatLabel(turnSeat) : '—'}
          </Typography>
          {typeof uno.winner === 'number' && (
            <Typography variant="body2" sx={{ fontWeight: 700 }} align="center">
              Winner: {seatLabel(uno.winner)}
            </Typography>
          )}
        </Stack>
      </Paper>

      <Typography variant="subtitle1" gutterBottom align="center">
        Your Hand
      </Typography>
      {(uno.your_hand || []).length ? (
        <Paper
          variant="outlined"
          sx={{
            p: 1.25,
            mb: 2,
            borderColor:
              typeof mySeat === 'number' && mySeat >= 0 ? playerColors[mySeat % playerColors.length] : undefined,
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
            {(uno.your_hand || []).map((c) =>
              renderCardTile({
                key: c.idx,
                text: c.text,
                enabled: !!c.playable,
                onClick: () => sendClick(`play:${c.idx}`),
              })
            )}
          </Box>
        </Paper>
      ) : (
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }} align="center">
          No cards (yet).
        </Typography>
      )}

      {(!snapshot.popup?.active && (!!ctrlColors.length || !!ctrlDraw || !!ctrlEnd || !!ctrlPlayAgain || !!ctrlForceStart)) && (
        <>
          <Typography variant="subtitle1" gutterBottom align="center">
            Actions
          </Typography>
          <Paper
            variant="outlined"
            sx={{
              p: 1.25,
              mb: 2,
              borderColor:
                typeof mySeat === 'number' && mySeat >= 0 ? playerColors[mySeat % playerColors.length] : undefined,
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
              {!!ctrlColors.length &&
                ctrlColors.map((b) =>
                  renderCardTile({
                    key: b.id,
                    text: (b.id.split(':')[1] || 'WILD').toUpperCase(),
                    enabled: !!b.enabled,
                    onClick: () => sendClick(b.id),
                  })
                )}

              {!ctrlColors.length && (
                <>
                  {typeof uno.winner === 'number' && (
                    <>
                      {ctrlPlayAgain &&
                        renderCardTile({
                          key: ctrlPlayAgain.id,
                          text: 'PLAY',
                          enabled: !!ctrlPlayAgain.enabled,
                          onClick: () => sendClick(ctrlPlayAgain.id),
                          asBack: true,
                        })}
                      {ctrlForceStart &&
                        renderCardTile({
                          key: ctrlForceStart.id,
                          text: 'FORCE',
                          enabled: !!ctrlForceStart.enabled,
                          onClick: () => sendClick(ctrlForceStart.id),
                          asBack: true,
                        })}
                    </>
                  )}

                  {ctrlDraw &&
                    renderCardTile({
                      key: ctrlDraw.id,
                      text: 'DRAW',
                      enabled: !!ctrlDraw.enabled,
                      onClick: () => sendClick(ctrlDraw.id),
                      asBack: true,
                    })}
                  {ctrlEnd &&
                    renderCardTile({
                      key: ctrlEnd.id,
                      text: 'END',
                      enabled: !!ctrlEnd.enabled,
                      onClick: () => sendClick(ctrlEnd.id),
                      asBack: true,
                    })}
                </>
              )}
            </Box>

            {!!uno.awaiting_color && (
              <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block', textAlign: 'center' }}>
                Choose a color to continue.
              </Typography>
            )}

            {typeof uno.winner === 'number' && (
              <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block', textAlign: 'center' }}>
                Next round ready: {uno.next_round_ready_count ?? 0}/{uno.next_round_total ?? (uno.active_players?.length ?? 0)}
              </Typography>
            )}
          </Paper>
        </>
      )}

      {!!uno.active_players?.length && (
        <Box sx={{ mb: 2 }}>
          <Typography variant="subtitle1" gutterBottom align="center">
            Players
          </Typography>
          <Stack spacing={1} alignItems="center">
            {(uno.active_players || []).map((pidx) => (
              <Paper
                key={pidx}
                variant="outlined"
                sx={{
                  p: 1.25,
                  borderColor: playerColors[pidx % playerColors.length],
                  width: '100%',
                  maxWidth: 440,
                  textAlign: 'center',
                }}
              >
                <Typography variant="body2" sx={{ fontWeight: 700 }} align="center">
                  {seatLabel(pidx)}
                </Typography>
                <Typography variant="body2" color="text.secondary" align="center">
                  Cards: {uno.hand_counts?.[String(pidx)] ?? 0}
                  {turnSeat === pidx ? ' · (turn)' : ''}
                </Typography>
              </Paper>
            ))}
          </Stack>
        </Box>
      )}
    </>
  );
}
