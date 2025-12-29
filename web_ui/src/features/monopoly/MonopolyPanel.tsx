import React from 'react';
import { Box, Button, Paper, Stack, Typography } from '@mui/material';
import type { Snapshot } from '../../types';

type Props = {
  snapshot: Snapshot;
  seatLabel: (seat: number) => string;
  send: (obj: unknown) => void;
  playerColors: string[];
};

export default function MonopolyPanel({ snapshot, seatLabel, send, playerColors }: Props): React.ReactElement {
  return (
    <>
      {!!snapshot.panel_buttons?.length && !snapshot.popup?.active && (
        <>
          {typeof snapshot.monopoly?.current_turn_seat === 'number' && (
            <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
              Current turn: {seatLabel(snapshot.monopoly.current_turn_seat)}
            </Typography>
          )}
          <Typography variant="subtitle1" gutterBottom sx={{ mt: 2 }}>
            Actions
          </Typography>
          <Stack spacing={1}>
            {snapshot.panel_buttons.map((b) => (
              <Button
                key={b.id}
                variant="contained"
                disabled={!b.enabled}
                onClick={() => send({ type: 'click_button', id: b.id })}
              >
                {b.text || b.id}
              </Button>
            ))}
          </Stack>
        </>
      )}

      {!!snapshot.monopoly?.players?.length && (
        <>
          <Typography variant="subtitle1" gutterBottom sx={{ mt: 2 }}>
            Players
          </Typography>
          <Stack spacing={1}>
            {snapshot.monopoly.players
              .slice()
              .sort((a, b) => a.player_idx - b.player_idx)
              .map((p) => (
                <Paper
                  key={p.player_idx}
                  variant="outlined"
                  sx={{
                    p: 1.5,
                    borderColor: playerColors[p.player_idx % playerColors.length],
                  }}
                >
                  <Typography variant="body2" sx={{ fontWeight: 600 }}>
                    {seatLabel(p.player_idx)}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Balance: ${p.money}
                  </Typography>
                  {(p.jail_free_cards || 0) > 0 && (
                    <Typography variant="body2" color="text.secondary">
                      Get out of Jail: {'\u{1F511}'} x{p.jail_free_cards}
                    </Typography>
                  )}
                  {!!p.properties?.length && (
                    <Typography variant="body2" color="text.secondary">
                      Properties: {p.properties.map((pp) => pp.name || `#${pp.idx}`).join(', ')}
                    </Typography>
                  )}
                  {!p.properties?.length && (
                    <Typography variant="body2" color="text.secondary">
                      Properties: None
                    </Typography>
                  )}
                </Paper>
              ))}
          </Stack>
        </>
      )}

      {!!snapshot.history?.length && (
        <Box sx={{ mt: 2 }}>
          <Typography variant="subtitle1" gutterBottom>
            History
          </Typography>
          <Paper variant="outlined" sx={{ p: 1.5, maxHeight: 220, overflow: 'auto' }}>
            <Stack spacing={0.5}>
              {snapshot.history
                .slice()
                .reverse()
                .map((h, i) => (
                  <Typography key={i} variant="body2" color="text.secondary">
                    {h}
                  </Typography>
                ))}
            </Stack>
          </Paper>
        </Box>
      )}
    </>
  );
}
