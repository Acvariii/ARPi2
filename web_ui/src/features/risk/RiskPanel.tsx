import React, { useMemo } from 'react';
import {
  Box,
  Button,
  Chip,
  Divider,
  List,
  ListItemButton,
  ListItemText,
  Paper,
  Stack,
  Typography,
} from '@mui/material';
import type { Snapshot } from '../../types';
import GameBanner from '../../components/GameBanner';

export default function RiskPanel(props: {
  snapshot: Snapshot;
  send: (obj: unknown) => void;
  playerColors: string[];
  seatLabel: (seat: number) => string;
}): React.ReactElement {
  const { snapshot, send, playerColors, seatLabel } = props;
  const st = snapshot.risk;
  const mySeat = snapshot.your_player_slot;

  if (snapshot.server_state !== 'risk' || !st) return <></>;

  const territories = useMemo(() => {
    const arr = st?.territories || [];
    return Array.isArray(arr) ? arr : [];
  }, [st?.territories]);

  const visibleTerritories = useMemo(() => {
    if (!Array.isArray(territories)) return [];
    const phase = String(st?.phase || '');

    const myOwned = typeof mySeat === 'number' ? territories.filter((t: any) => t?.owner === mySeat) : territories;

    if (phase === 'initial_deploy' || phase === 'reinforce' || phase === 'fortify') {
      return myOwned;
    }

    if (phase === 'attack') {
      const selectedFrom = typeof (st as any)?.selected_from === 'number' ? (st as any).selected_from : null;
      const attackFrom = Array.isArray((st as any)?.attack_from_tids) ? ((st as any).attack_from_tids as number[]) : [];
      const attackTo = Array.isArray((st as any)?.attack_to_tids) ? ((st as any).attack_to_tids as number[]) : [];

      // If an attacker is selected, show only attackable defenders + the selected attacker.
      if (typeof mySeat === 'number' && typeof selectedFrom === 'number') {
        const fromTerr = territories.find((t: any) => Number(t?.tid) === selectedFrom);
        const defenders = territories.filter((t: any) => attackTo.includes(Number(t?.tid)));
        return fromTerr ? [fromTerr, ...defenders] : defenders;
      }

      // Otherwise show only possible attackers.
      return territories.filter((t: any) => attackFrom.includes(Number(t?.tid)));
    }

    return territories;
  }, [territories, st?.phase, (st as any)?.selected_from, (st as any)?.attack_from_tids, (st as any)?.attack_to_tids, mySeat]);

  const byContinent = useMemo(() => {
    const m = new Map<string, any[]>();
    for (const t of visibleTerritories) {
      const c = String(t?.continent || '');
      if (!m.has(c)) m.set(c, []);
      m.get(c)!.push(t);
    }
    for (const [k, v] of m) {
      v.sort((a, b) => String(a?.name || '').localeCompare(String(b?.name || '')));
      m.set(k, v);
    }
    return Array.from(m.entries()).sort((a, b) => a[0].localeCompare(b[0]));
  }, [visibleTerritories]);

  const showTerritories = st?.state === 'playing';

  const isMyTurn = typeof mySeat === 'number' && typeof st?.current_turn_seat === 'number' && mySeat === st.current_turn_seat;

  const pick = (tid: number) => {
    if (!Number.isFinite(tid)) return;
    if (String(st?.phase || '') === 'conquer_move') return;
    send({ type: 'click_button', id: `pick:${tid}` });
  };

  const actionButtons = snapshot.panel_buttons || [];

  const ownerChip = (owner: number | null | undefined) => {
    if (typeof owner !== 'number') return <Chip size="small" label="—" variant="outlined" />;
    const col = playerColors[owner] || undefined;
    return <Chip size="small" label={seatLabel(owner)} sx={col ? { bgcolor: col, color: '#000' } : undefined} />;
  };

  return (
    <Stack spacing={1.25} sx={{ animation: 'fadeInUp 0.4s ease-out' }}>
      <GameBanner game="risk" />
      <Paper variant="outlined" sx={{ p: 1.25 }}>
        {typeof st?.winner === 'number' ? (
          <Typography variant="body1" sx={{ fontWeight: 800, animation: 'winnerShimmer 2s linear infinite, glowText 1.5s ease-in-out infinite' }} align="center">
            🏆 Winner: {seatLabel(st.winner)}
          </Typography>
        ) : (
          <Stack spacing={0.75}>
            <Stack direction="row" spacing={1} justifyContent="center" flexWrap="wrap" useFlexGap>
              {/* Phase badge */}
              {(() => {
                const phase = String(st?.phase || '');
                const phaseInfo: Record<string, { icon: string; color: string }> = {
                  initial_deploy: { icon: '🚩', color: '#7b1fa2' },
                  reinforce: { icon: '➕', color: '#1565c0' },
                  attack: { icon: '⚔️', color: '#c62828' },
                  conquer_move: { icon: '💪', color: '#e65100' },
                  fortify: { icon: '🛡️', color: '#2e7d32' },
                };
                const info = phaseInfo[phase] ?? { icon: '🎮', color: '#37474f' };
                return (
                  <Chip
                    label={`${info.icon} ${phase.replace('_', ' ').toUpperCase()}`}
                    size="small"
                    sx={{ bgcolor: info.color, color: '#fff', fontWeight: 700, height: 24, fontSize: '0.75rem', animation: 'badgePop 0.4s ease-out' }}
                  />
                );
              })()}
              {isMyTurn && (
                <Chip label="Your Turn" size="small" color="primary" sx={{ height: 24, fontWeight: 700, animation: 'pulseScale 1.5s ease-in-out infinite' }} />
              )}
              {st?.phase === 'initial_deploy' && (
                <Chip label={`Pool: ${(st as any)?.initial_deploy_pool ?? 0}`} size="small" variant="outlined" sx={{ height: 24 }} />
              )}
              {typeof st?.reinforcements_left === 'number' && st.reinforcements_left > 0 && (
                <Chip label={`+${st.reinforcements_left} reinforce`} size="small" sx={{ bgcolor: '#1565c0', color: '#fff', height: 24 }} />
              )}
            </Stack>
            <Typography variant="body2" color="text.secondary" align="center">
              Turn: {typeof st?.current_turn_seat === 'number' ? seatLabel(st.current_turn_seat) : '—'}
            </Typography>
          </Stack>
        )}
        {st?.last_event ? (
          <Typography variant="caption" color="text.secondary" display="block" align="center" sx={{ mt: 0.5, animation: 'slideInRight 0.4s ease-out' }}>
            {st.last_event}
          </Typography>
        ) : null}
      </Paper>

      {st?.state === 'playing' && (st as any)?.your_mission ? (
        <Paper variant="outlined" sx={{ p: 1.25 }}>
          <Typography variant="subtitle1" gutterBottom>
            Mission
          </Typography>
          <Typography variant="body2" color="text.secondary">
            {(st as any).your_mission}
          </Typography>
        </Paper>
      ) : null}

      <Paper variant="outlined" sx={{ p: 1.25 }}>
        <Typography variant="subtitle1" gutterBottom>
          Actions
        </Typography>
        <Stack direction="row" spacing={1} useFlexGap flexWrap="wrap">
          {actionButtons.length ? (
            actionButtons.map((b, bIdx) => (
              <Button
                key={b.id}
                variant="contained"
                size="small"
                disabled={!b.enabled}
                onClick={() => send({ type: 'click_button', id: b.id })}
                sx={{ animation: `bounceIn 0.35s ease-out ${bIdx * 0.05}s both` }}
              >
                {b.text}
              </Button>
            ))
          ) : (
            <Typography variant="body2" color="text.secondary">
              No actions
            </Typography>
          )}
          {!isMyTurn && st?.state === 'playing' ? (
            <Chip size="small" label="Waiting" variant="outlined" />
          ) : null}
        </Stack>
      </Paper>

      {showTerritories ? (
        <Paper variant="outlined" sx={{ p: 1.25 }}>
          <Typography variant="subtitle1" gutterBottom>
            Territories (tap to select)
          </Typography>
          <Typography variant="caption" color="text.secondary" display="block" sx={{ mb: 1 }}>
            Selection is used for Reinforce/Attack/Fortify.
          </Typography>
          <Divider sx={{ mb: 1 }} />

          <Box sx={{ maxHeight: '52vh', overflowY: 'auto' }}>
            {byContinent.map(([cont, list]) => (
              <Box key={cont} sx={{ mb: 1.5 }}>
                <Typography variant="overline" color="text.secondary">
                  {cont || 'Other'}
                </Typography>
                <List dense disablePadding>
                  {list.map((t: any) => {
                    const tid = Number(t?.tid);
                    const selected = tid === st?.selected_from || tid === st?.selected_to;
                    const owner = typeof t?.owner === 'number' ? (t.owner as number) : null;
                    const troops = typeof t?.troops === 'number' ? t.troops : 0;
                    const ownerColor = owner !== null && owner >= 0 ? playerColors[owner % playerColors.length] : undefined;

                    return (
                      <ListItemButton
                        key={String(tid)}
                        onClick={() => pick(tid)}
                        selected={selected}
                        sx={{
                          borderRadius: 1,
                          mb: 0.25,
                          borderLeft: selected ? `4px solid #f9a825` : undefined,
                        }}
                      >
                        <ListItemText
                          primary={
                            <Stack direction="row" spacing={1} alignItems="center">
                              <Typography variant="body2" sx={{ fontWeight: 700, flex: 1 }}>
                                {String(t?.name || `T${tid}`)}
                              </Typography>
                              {ownerChip(owner)}
                              <Chip
                                size="small"
                                label={`${troops}`}
                                sx={{
                                  bgcolor: ownerColor ?? '#546e7a',
                                  color: '#fff',
                                  fontWeight: 900,
                                  minWidth: 28,
                                  height: 20,
                                  fontSize: '0.72rem',
                                }}
                              />
                              {tid === st?.selected_from ? <Chip size="small" label="From" color="warning" sx={{ height: 18, fontSize: '0.65rem' }} /> : null}
                              {tid === st?.selected_to ? <Chip size="small" label="To" color="success" sx={{ height: 18, fontSize: '0.65rem' }} /> : null}
                            </Stack>
                          }
                        />
                      </ListItemButton>
                    );
                  })}
                </List>
              </Box>
            ))}
          </Box>
        </Paper>
      ) : null}
    </Stack>
  );
}
