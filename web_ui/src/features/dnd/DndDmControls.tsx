import React, { useEffect, useState } from 'react';
import {
  Button,
  Card,
  CardContent,
  MenuItem,
  Stack,
  TextField,
  Typography,
} from '@mui/material';
import type { Snapshot } from '../../types';

type Props = {
  snapshot: Snapshot;
  seatLabel: (seat: number) => string;
  send: (obj: unknown) => void;
};

export default function DndDmControls({ snapshot, seatLabel, send }: Props): React.ReactElement {
  const [dndBackground, setDndBackground] = useState<string>('');
  const [dndMonster, setDndMonster] = useState<string>('');

  const [dndGiveTarget, setDndGiveTarget] = useState<number>(0);
  const [dndItemName, setDndItemName] = useState<string>('');
  const [dndItemKind, setDndItemKind] = useState<'consumable' | 'gear' | 'misc'>('consumable');
  const [dndConsumableHeal, setDndConsumableHeal] = useState<number>(5);
  const [dndGearSlot, setDndGearSlot] = useState<string>('helmet');
  const [dndGearAcBonus, setDndGearAcBonus] = useState<number>(0);
  const [dndGearBonuses, setDndGearBonuses] = useState<Record<string, number>>({
    Strength: 0,
    Dexterity: 0,
    Constitution: 0,
    Intelligence: 0,
    Wisdom: 0,
    Charisma: 0,
  });

  useEffect(() => {
    const ms = snapshot?.dnd?.monsters || [];
    if (!dndMonster && ms.length) setDndMonster(ms[0]);
  }, [dndMonster, snapshot?.dnd?.monsters]);

  // Keep give-target in range as player list changes.
  useEffect(() => {
    const rows = (snapshot.dnd?.players || []).filter((p) => p.selected && !p.is_dm);
    if (!rows.length) return;
    const found = rows.find((p) => p.player_idx === dndGiveTarget);
    if (!found) setDndGiveTarget(rows[0].player_idx);
  }, [dndGiveTarget, snapshot.dnd?.players]);

  const DND_EQUIP_SLOTS = ['helmet', 'chest', 'leggings', 'boots', 'sword', 'bow', 'staff', 'knife'];
  const DND_ABILITIES = ['Strength', 'Dexterity', 'Constitution', 'Intelligence', 'Wisdom', 'Charisma'];

  return (
    <>
      <Typography variant="subtitle2" sx={{ mt: 2 }}>
        DM Controls
      </Typography>

      <Stack spacing={2} sx={{ mt: 1 }}>
        <Card variant="outlined">
          <CardContent>
            <Typography variant="subtitle2" gutterBottom>
              Scene
            </Typography>
            <Stack spacing={1.25}>
              <TextField
                label="Local Background"
                size="small"
                select
                value={dndBackground}
                onChange={(e) => setDndBackground(e.target.value)}
                fullWidth
                helperText={
                  (snapshot?.dnd?.background_files || []).length
                    ? 'Uses files from games/dnd/backgrounds (no external APIs).'
                    : 'No local backgrounds found in games/dnd/backgrounds.'
                }
              >
                <MenuItem value="">
                  <em>Select a background…</em>
                </MenuItem>
                {(snapshot?.dnd?.background_files || []).map((f) => (
                  <MenuItem key={f} value={f}>
                    {f}
                  </MenuItem>
                ))}
              </TextField>

              <Button
                variant="contained"
                disabled={!dndBackground.trim()}
                onClick={() => send({ type: 'dnd_dm_set_background_file', background_file: dndBackground.trim() })}
              >
                Set Background
              </Button>
            </Stack>
          </CardContent>
        </Card>

        <Card variant="outlined">
          <CardContent>
            <Typography variant="subtitle2" gutterBottom>
              Encounter
            </Typography>
            <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1} alignItems={{ sm: 'center' }}>
              <TextField
                label="Spawn Enemy"
                size="small"
                select
                value={dndMonster}
                onChange={(e) => setDndMonster(e.target.value)}
                fullWidth
              >
                {(snapshot.dnd?.monsters || []).map((m) => (
                  <MenuItem key={m} value={m}>
                    {m}
                  </MenuItem>
                ))}
              </TextField>
              <Button variant="contained" disabled={!dndMonster} onClick={() => send({ type: 'dnd_dm_spawn_enemy', monster: dndMonster })}>
                Spawn
              </Button>
            </Stack>
          </CardContent>
        </Card>

        <Card variant="outlined">
          <CardContent>
            <Typography variant="subtitle2" gutterBottom>
              Items
            </Typography>
            <Stack spacing={1.25}>
              <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1} alignItems={{ sm: 'center' }}>
                <TextField
                  label="Target"
                  size="small"
                  select
                  value={String(dndGiveTarget)}
                  onChange={(e) => setDndGiveTarget(Number(e.target.value))}
                  sx={{ minWidth: 180 }}
                >
                  {(snapshot.dnd?.players || [])
                    .filter((p) => p.selected && !p.is_dm)
                    .map((p) => (
                      <MenuItem key={p.player_idx} value={String(p.player_idx)}>
                        {seatLabel(p.player_idx)}
                      </MenuItem>
                    ))}
                </TextField>

                <TextField
                  label="Item Name"
                  size="small"
                  value={dndItemName}
                  onChange={(e) => setDndItemName(e.target.value)}
                  fullWidth
                />

                <TextField
                  label="Kind"
                  size="small"
                  select
                  value={dndItemKind}
                  onChange={(e) => setDndItemKind(e.target.value as any)}
                  sx={{ minWidth: 160 }}
                >
                  <MenuItem value="consumable">Consumable</MenuItem>
                  <MenuItem value="gear">Gear</MenuItem>
                  <MenuItem value="misc">Misc</MenuItem>
                </TextField>
              </Stack>

              {dndItemKind === 'consumable' && (
                <TextField
                  label="Heal Amount"
                  size="small"
                  type="number"
                  value={String(dndConsumableHeal)}
                  onChange={(e) => setDndConsumableHeal(Number(e.target.value))}
                />
              )}

              {dndItemKind === 'gear' && (
                <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1}>
                  <TextField
                    label="Slot"
                    size="small"
                    select
                    value={dndGearSlot}
                    onChange={(e) => setDndGearSlot(e.target.value)}
                    sx={{ minWidth: 160 }}
                  >
                    {DND_EQUIP_SLOTS.map((s) => (
                      <MenuItem key={s} value={s}>
                        {s}
                      </MenuItem>
                    ))}
                  </TextField>

                  <TextField
                    label="AC Bonus"
                    size="small"
                    type="number"
                    value={String(dndGearAcBonus)}
                    onChange={(e) => setDndGearAcBonus(Number(e.target.value))}
                    sx={{ minWidth: 140 }}
                  />

                  <TextField
                    label="Bonuses"
                    size="small"
                    select
                    value=""
                    sx={{ display: 'none' }}
                  />
                </Stack>
              )}

              {dndItemKind === 'gear' && (
                <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1} sx={{ flexWrap: 'wrap' }}>
                  {DND_ABILITIES.map((a) => (
                    <TextField
                      key={a}
                      label={`${a} Bonus`}
                      size="small"
                      type="number"
                      value={String(dndGearBonuses[a] ?? 0)}
                      onChange={(e) => setDndGearBonuses((prev) => ({ ...prev, [a]: Number(e.target.value) }))}
                      sx={{ minWidth: 180 }}
                    />
                  ))}
                </Stack>
              )}

              <Button
                variant="contained"
                disabled={!dndItemName.trim()}
                onClick={() =>
                  send({
                    type: 'dnd_dm_give_item',
                    target: dndGiveTarget,
                    item: {
                      name: dndItemName.trim(),
                      kind: dndItemKind,
                      ...(dndItemKind === 'consumable'
                        ? { effect: { type: 'heal', amount: dndConsumableHeal } }
                        : {}),
                      ...(dndItemKind === 'gear'
                        ? { slot: dndGearSlot, ac_bonus: dndGearAcBonus, ability_bonuses: dndGearBonuses }
                        : {}),
                    },
                  })
                }
              >
                Give Item
              </Button>
            </Stack>
          </CardContent>
        </Card>
      </Stack>
    </>
  );
}
