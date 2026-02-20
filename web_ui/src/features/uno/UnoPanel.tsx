import React from 'react';
import { Box, Button, Paper, Stack, Typography } from '@mui/material';
import type { Snapshot } from '../../types';
import UnoCardTile from '../../components/UnoCardTile';
import GameBanner from '../../components/GameBanner';

type Props = {
  snapshot: Snapshot;
  seatLabel: (seat: number) => string;
  send: (obj: unknown) => void;
  playerColors: string[];
};

export default function UnoPanel({ snapshot, seatLabel, send, playerColors }: Props): React.ReactElement {
  if (snapshot.server_state !== 'uno' || !snapshot.uno) return <></>;
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

  const renderCardTile = (opts: {
    key: string | number;
    text: string;
    onClick?: () => void;
    enabled?: boolean;
    asBack?: boolean;
  }) => {
    const enabled = opts.enabled ?? true;
    const clickable = !!opts.onClick && enabled && !snapshot.popup?.active;

    return (
      <UnoCardTile
        key={String(opts.key)}
        text={opts.text}
        asBack={!!opts.asBack}
        enabled={clickable}
        onClick={opts.onClick}
        width={74}
      />
    );
  };

  return (
    <>
      <GameBanner game="uno" />
      <Paper variant="outlined" sx={{ p: 1.5, mb: 2 }}>
        <Stack spacing={1}>
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
