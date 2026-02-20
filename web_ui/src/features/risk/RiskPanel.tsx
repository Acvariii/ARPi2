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
    <Stack spacing={1.25}>
      <GameBanner game="risk" />
      <Paper variant="outlined" sx={{ p: 1.25 }}>
        <Typography variant="body2" color="text.secondary" align="center">
          {typeof st?.winner === 'number'
            ? `Winner: ${seatLabel(st.winner)}`
            : st?.phase === 'initial_deploy'
              ? `Initial Deploy · Pool: ${(st as any)?.initial_deploy_pool ?? 0}`
              : `Turn: ${typeof st?.current_turn_seat === 'number' ? seatLabel(st.current_turn_seat) : '—'} · Phase: ${
                  st?.phase || '—'
                } · Reinforcements: ${st?.reinforcements_left ?? 0}`}
        </Typography>
        {st?.last_event ? (
          <Typography variant="caption" color="text.secondary" display="block" align="center" sx={{ mt: 0.5 }}>
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
            actionButtons.map((b) => (
              <Button
                key={b.id}
                variant="contained"
                size="small"
                disabled={!b.enabled}
                onClick={() => send({ type: 'click_button', id: b.id })}
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

                    return (
                      <ListItemButton
                        key={String(tid)}
                        onClick={() => pick(tid)}
                        selected={selected}
                        sx={{
                          borderRadius: 1,
                          mb: 0.25,
                        }}
                      >
                        <ListItemText
                          primary={
                            <Stack direction="row" spacing={1} alignItems="center">
                              <Typography variant="body2" sx={{ fontWeight: 700 }}>
                                {String(t?.name || `T${tid}`)}
                              </Typography>
                              {ownerChip(owner)}
                              <Chip size="small" label={`${troops}`} variant="outlined" />
                              {tid === st?.selected_from ? <Chip size="small" label="From" /> : null}
                              {tid === st?.selected_to ? <Chip size="small" label="To" /> : null}
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
