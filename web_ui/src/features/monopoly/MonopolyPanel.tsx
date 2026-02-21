import React from 'react';
import { Box, Button, Chip, Paper, Stack, Typography } from '@mui/material';
import type { Snapshot } from '../../types';
import GameBanner from '../../components/GameBanner';

const MONOPOLY_SPACES = [
  'Go', 'Mediterranean Ave', 'Community Chest', 'Baltic Ave', 'Income Tax',
  'Reading Railroad', 'Oriental Ave', 'Chance', 'Vermont Ave', 'Connecticut Ave',
  'Just Visiting / Jail', 'St. Charles Place', 'Electric Company', 'States Ave', 'Virginia Ave',
  'Pennsylvania Railroad', 'St. James Place', 'Community Chest', 'Tennessee Ave', 'New York Ave',
  'Free Parking', 'Kentucky Ave', 'Chance', 'Indiana Ave', 'Illinois Ave',
  'B&O Railroad', 'Atlantic Ave', 'Ventnor Ave', 'Water Works', 'Marvin Gardens',
  'Go To Jail', 'Pacific Ave', 'N. Carolina Ave', 'Community Chest', 'Pennsylvania Ave',
  'Short Line Railroad', 'Chance', 'Park Place', 'Luxury Tax', 'Boardwalk',
];

const PROP_COLOR: Record<number, { bg: string; fg: string }> = {
  1: { bg: '#9c27b0', fg: '#fff' }, 3: { bg: '#9c27b0', fg: '#fff' },
  6: { bg: '#00bcd4', fg: '#000' }, 8: { bg: '#00bcd4', fg: '#000' }, 9: { bg: '#00bcd4', fg: '#000' },
  11: { bg: '#e91e63', fg: '#fff' }, 13: { bg: '#e91e63', fg: '#fff' }, 14: { bg: '#e91e63', fg: '#fff' },
  16: { bg: '#ff9800', fg: '#000' }, 18: { bg: '#ff9800', fg: '#000' }, 19: { bg: '#ff9800', fg: '#000' },
  21: { bg: '#f44336', fg: '#fff' }, 23: { bg: '#f44336', fg: '#fff' }, 24: { bg: '#f44336', fg: '#fff' },
  26: { bg: '#fdd835', fg: '#000' }, 27: { bg: '#fdd835', fg: '#000' }, 29: { bg: '#fdd835', fg: '#000' },
  31: { bg: '#4caf50', fg: '#fff' }, 32: { bg: '#4caf50', fg: '#fff' }, 34: { bg: '#4caf50', fg: '#fff' },
  37: { bg: '#1a237e', fg: '#fff' }, 39: { bg: '#1a237e', fg: '#fff' },
  5: { bg: '#333', fg: '#fff' }, 15: { bg: '#333', fg: '#fff' }, 25: { bg: '#333', fg: '#fff' }, 35: { bg: '#333', fg: '#fff' },
  12: { bg: '#9e9e9e', fg: '#000' }, 28: { bg: '#9e9e9e', fg: '#000' },
};

type Props = {
  snapshot: Snapshot;
  seatLabel: (seat: number) => string;
  send: (obj: unknown) => void;
  playerColors: string[];
};

export default function MonopolyPanel({ snapshot, seatLabel, send, playerColors }: Props): React.ReactElement {
  if (snapshot.server_state !== 'monopoly' || !snapshot.monopoly) return <></>;

  const mono = snapshot.monopoly;
  const turnSeat = typeof mono.current_turn_seat === 'number' ? mono.current_turn_seat : null;

  return (
    <Stack spacing={1.5} sx={{ animation: 'fadeInUp 0.4s ease-out' }}>
      <GameBanner game="monopoly" />

      {/* Turn indicator banner */}
      {turnSeat !== null && (
        <Paper
          variant="outlined"
          sx={{
            p: 1.25,
            borderColor: playerColors[turnSeat % playerColors.length],
            borderWidth: 2,
            bgcolor: `${playerColors[turnSeat % playerColors.length]}22`,
            animation: 'turnGlow 2s ease-in-out infinite',
          }}
        >
          <Typography variant="body1" sx={{ fontWeight: 800 }} align="center">
            🎲 {seatLabel(turnSeat)}&apos;s Turn
          </Typography>
        </Paper>
      )}

      {/* Action buttons */}
      {!!snapshot.panel_buttons?.length && !snapshot.popup?.active && (
        <Paper variant="outlined" sx={{ p: 1.25 }}>
          <Typography variant="subtitle2" gutterBottom>Actions</Typography>
          <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
            {snapshot.panel_buttons.map((b, bIdx) => (
              <Button
                key={b.id}
                variant="contained"
                size="small"
                disabled={!b.enabled}
                onClick={() => send({ type: 'click_button', id: b.id })}
                sx={{ flex: '1 1 auto', minWidth: 100, animation: `bounceIn 0.35s ease-out ${bIdx * 0.05}s both` }}
              >
                {b.text || b.id}
              </Button>
            ))}
          </Stack>
        </Paper>
      )}

      {/* Players */}
      {!!mono.players?.length && (
        <Stack spacing={1}>
          {mono.players
            .slice()
            .sort((a, b) => a.player_idx - b.player_idx)
            .map((p) => {
              const isTurn = p.player_idx === turnSeat;
              const color = playerColors[p.player_idx % playerColors.length];
              const pos = typeof p.position === 'number' ? p.position : null;
              const inJail = !!p.in_jail;
              const spaceName = pos !== null ? (MONOPOLY_SPACES[pos] ?? `Space ${pos}`) : null;

              return (
                <Paper
                  key={p.player_idx}
                  variant="outlined"
                  sx={{
                    p: 1.5,
                    borderColor: isTurn ? color : `${color}88`,
                    borderWidth: isTurn ? 2 : 1,
                    bgcolor: isTurn ? `${color}18` : 'background.paper',
                    animation: `fadeInUp 0.3s ease-out ${p.player_idx * 0.07}s both`,
                  }}
                >
                  <Stack direction="row" justifyContent="space-between" alignItems="flex-start">
                    <Stack spacing={0.5} flex={1} minWidth={0}>
                      <Stack direction="row" spacing={0.75} alignItems="center" flexWrap="wrap">
                        <Typography variant="body2" sx={{ fontWeight: 800 }}>
                          {seatLabel(p.player_idx)}
                        </Typography>
                        {isTurn && (
                          <Chip label="Turn" size="small" color="primary" sx={{ height: 18, fontSize: '0.65rem', animation: 'badgePop 0.3s ease-out' }} />
                        )}
                        {inJail && (
                          <Chip
                            label="🔒 Jail"
                            size="small"
                            sx={{ height: 18, fontSize: '0.65rem', bgcolor: '#c62828', color: '#fff', animation: 'blink 0.8s ease-in-out 3' }}
                          />
                        )}
                      </Stack>
                      {spaceName && (
                        <Typography variant="caption" color="text.secondary">
                          📍 {spaceName}
                        </Typography>
                      )}
                      {(p.jail_free_cards || 0) > 0 && (
                        <Typography variant="caption" color="text.secondary">
                          🗝 Get Out of Jail &times;{p.jail_free_cards}
                        </Typography>
                      )}
                    </Stack>
                    <Box sx={{ textAlign: 'right', ml: 1, flexShrink: 0 }}>
                      <Typography variant="h6" sx={{ fontWeight: 900, color: '#4caf50', lineHeight: 1.2, animation: isTurn ? 'potPop 0.4s ease-out' : undefined }}>
                        ${p.money.toLocaleString()}
                      </Typography>
                      {!!p.properties?.length && (
                        <Typography variant="caption" color="text.secondary">
                          {p.properties.length} {p.properties.length === 1 ? 'property' : 'properties'}
                        </Typography>
                      )}
                    </Box>
                  </Stack>
                  {!!p.properties?.length && (
                    <Box sx={{ mt: 1, display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                      {p.properties.map((pp) => {
                        const c = PROP_COLOR[pp.idx] ?? { bg: '#9e9e9e', fg: '#000' };
                        return (
                          <Chip
                            key={pp.idx}
                            label={pp.name || `#${pp.idx}`}
                            size="small"
                            sx={{ bgcolor: c.bg, color: c.fg, fontWeight: 700, fontSize: '0.65rem', height: 20 }}
                          />
                        );
                      })}
                    </Box>
                  )}
                </Paper>
              );
            })}
        </Stack>
      )}

      {/* History */}
      {!!snapshot.history?.length && (
        <Paper variant="outlined" sx={{ p: 1.25, maxHeight: 180, overflow: 'auto' }}>
          <Typography variant="subtitle2" gutterBottom>History</Typography>
          <Stack spacing={0.25}>
            {snapshot.history
              .slice()
              .reverse()
              .map((h, i) => (
                <Typography key={i} variant="caption" color="text.secondary" display="block" sx={i === 0 ? { animation: 'slideInRight 0.3s ease-out', fontWeight: 700 } : undefined}>
                  {h}
                </Typography>
              ))}
          </Stack>
        </Paper>
      )}
    </Stack>
  );
}
