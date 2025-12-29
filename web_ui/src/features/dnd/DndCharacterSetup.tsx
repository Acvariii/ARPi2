import React, { useCallback, useEffect, useMemo, useState } from 'react';
import {
  Box,
  Button,
  Card,
  CardContent,
  Divider,
  MenuItem,
  Paper,
  Stack,
  TextField,
  Typography,
} from '@mui/material';
import type { Snapshot } from '../../types';
import DndDicePanel from './DndDicePanel';

type Props = {
  snapshot: Snapshot;
  isDm: boolean;
  isSeated: boolean;
  myDndRow: NonNullable<Snapshot['dnd']>['players'] extends Array<infer T> ? T | null : any;
  seatLabel: (seat: number) => string;
  send: (obj: unknown) => void;
  dndEmojiForRace: (race: string) => string;
  dndEmojiForClass: (cls: string) => string;
};

export default function DndCharacterSetup(props: Props): React.ReactElement {
  const { snapshot, isDm, isSeated, myDndRow, seatLabel, send, dndEmojiForRace, dndEmojiForClass } = props;

  const [dndName, setDndName] = useState<string>('');
  const [dndRace, setDndRace] = useState<string>('');
  const [dndClass, setDndClass] = useState<string>('');

  const [dndBackgroundAnswers, setDndBackgroundAnswers] = useState<Record<string, string>>({});
  const [dndCreateStep, setDndCreateStep] = useState<'race' | 'class' | 'abilities' | 'background' | 'confirm'>('race');
  const [dndAbilities, setDndAbilities] = useState<Record<string, number>>({
    Strength: 8,
    Dexterity: 8,
    Constitution: 8,
    Intelligence: 8,
    Wisdom: 8,
    Charisma: 8,
  });

  const dndBackgroundQuestions = useMemo(() => {
    const qs = snapshot?.dnd?.background_questions;
    return Array.isArray(qs) ? qs : [];
  }, [snapshot?.dnd?.background_questions]);

  const dndBackgroundQuestionSig = useMemo(() => dndBackgroundQuestions.map((q) => q.id).join('|'), [dndBackgroundQuestions]);

  useEffect(() => {
    setDndBackgroundAnswers({});
  }, [dndBackgroundQuestionSig]);

  // Seed race/class defaults when D&D snapshot arrives.
  useEffect(() => {
    const races = snapshot?.dnd?.races || [];
    const classes = snapshot?.dnd?.classes || [];
    if (!dndRace && races.length) setDndRace(races[0]);
    if (!dndClass && classes.length) setDndClass(classes[0]);
  }, [dndClass, dndRace, snapshot?.dnd?.classes, snapshot?.dnd?.races]);

  const dndPointBuyRemaining = useMemo(() => {
    const cost: Record<number, number> = { 8: 0, 9: 1, 10: 2, 11: 3, 12: 4, 13: 5, 14: 7, 15: 9 };
    let spent = 0;
    for (const v of Object.values(dndAbilities)) spent += cost[v] ?? 999;
    return 27 - spent;
  }, [dndAbilities]);

  const dndCanInc = useCallback(
    (ability: string) => {
      const v = dndAbilities[ability] ?? 8;
      if (v >= 15) return false;
      const next = v + 1;
      const cost: Record<number, number> = { 8: 0, 9: 1, 10: 2, 11: 3, 12: 4, 13: 5, 14: 7, 15: 9 };
      const delta = (cost[next] ?? 999) - (cost[v] ?? 999);
      return dndPointBuyRemaining - delta >= 0;
    },
    [dndAbilities, dndPointBuyRemaining]
  );

  const dndCanDec = useCallback(
    (ability: string) => {
      const v = dndAbilities[ability] ?? 8;
      return v > 8;
    },
    [dndAbilities]
  );

  const dndAdjustAbility = useCallback((ability: string, delta: number) => {
    setDndAbilities((prev) => {
      const v = prev[ability] ?? 8;
      const next = Math.max(8, Math.min(15, v + delta));
      return { ...prev, [ability]: next };
    });
  }, []);

  const dndResetAbilities = useCallback(() => {
    setDndAbilities({
      Strength: 8,
      Dexterity: 8,
      Constitution: 8,
      Intelligence: 8,
      Wisdom: 8,
      Charisma: 8,
    });
  }, []);

  const setBgAnswer = useCallback((id: string, value: string) => {
    setDndBackgroundAnswers((prev) => ({ ...prev, [id]: value }));
  }, []);

  return (
    <>
      <Typography variant="subtitle1" gutterBottom sx={{ mt: 2 }}>
        D&amp;D Character Setup
      </Typography>

      {isDm ? (
        <Typography variant="body2" color="text.secondary">
          Waiting for players to create or load characters.
        </Typography>
      ) : (
        <>
          {myDndRow?.has_character ? (
            <Paper variant="outlined" sx={{ p: 1.5 }}>
              <Typography variant="body2" sx={{ fontWeight: 600 }}>
                Ready: {myDndRow.name}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                {myDndRow.race} {myDndRow.char_class} · HP {myDndRow.hp} · AC {myDndRow.ac}
              </Typography>
              {!!myDndRow.background && (
                <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
                  Background: {myDndRow.background}
                </Typography>
              )}
              {!!myDndRow.skills?.length && (
                <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
                  Skills: {myDndRow.skills.join(', ')}
                </Typography>
              )}
              {!!myDndRow.feats?.length && (
                <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
                  Feat: {myDndRow.feats.join(', ')}
                </Typography>
              )}
              {!!myDndRow.features?.length && (
                <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
                  Features: {myDndRow.features.join(' · ')}
                </Typography>
              )}
              {!!myDndRow.inventory?.length && (
                <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
                  Inventory: {(myDndRow.inventory || []).map((it: any) => String(it?.name || it)).join(', ')}
                </Typography>
              )}
            </Paper>
          ) : (
            <Stack spacing={1}>
              <Button
                variant="contained"
                disabled={!myDndRow?.has_saved}
                onClick={() => send({ type: 'dnd_load_character' })}
              >
                {myDndRow?.has_saved ? 'Load Saved Character' : 'No Saved Character'}
              </Button>

              <Divider />

              <Typography variant="subtitle2">Create New Character</Typography>

              {dndCreateStep === 'race' && (
                <>
                  <Typography variant="body2" color="text.secondary">
                    Step 1: Choose a race
                  </Typography>
                  <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
                    {(snapshot.dnd?.races || []).map((r) => (
                      <Card
                        key={r}
                        variant="outlined"
                        sx={{
                          cursor: 'pointer',
                          width: { xs: '100%', sm: 200 },
                          borderColor: r === dndRace ? 'primary.main' : undefined,
                        }}
                        onClick={() => setDndRace(r)}
                      >
                        <CardContent sx={{ py: 1.25, '&:last-child': { pb: 1.25 } }}>
                          <Typography variant="body2" sx={{ fontWeight: 700 }}>
                            {r}
                          </Typography>
                          <Typography variant="h3" sx={{ textAlign: 'center', mt: 1 }}>
                            {dndEmojiForRace(r)}
                          </Typography>
                        </CardContent>
                      </Card>
                    ))}
                  </Box>
                  <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1} sx={{ mt: 1 }}>
                    <Button variant="contained" disabled={!dndRace} onClick={() => setDndCreateStep('class')}>
                      Next
                    </Button>
                  </Stack>
                </>
              )}

              {dndCreateStep === 'class' && (
                <>
                  <Typography variant="body2" color="text.secondary">
                    Step 2: Choose a class
                  </Typography>
                  <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
                    {(snapshot.dnd?.classes || []).map((c) => (
                      <Card
                        key={c}
                        variant="outlined"
                        sx={{
                          cursor: 'pointer',
                          width: { xs: '100%', sm: 200 },
                          borderColor: c === dndClass ? 'primary.main' : undefined,
                        }}
                        onClick={() => setDndClass(c)}
                      >
                        <CardContent sx={{ py: 1.25, '&:last-child': { pb: 1.25 } }}>
                          <Typography variant="body2" sx={{ fontWeight: 700 }}>
                            {c}
                          </Typography>
                          <Typography variant="h3" sx={{ textAlign: 'center', mt: 1 }}>
                            {dndEmojiForClass(c)}
                          </Typography>
                        </CardContent>
                      </Card>
                    ))}
                  </Box>
                  <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1} sx={{ mt: 1 }}>
                    <Button variant="outlined" onClick={() => setDndCreateStep('race')}>
                      Back
                    </Button>
                    <Button variant="contained" disabled={!dndClass} onClick={() => setDndCreateStep('abilities')}>
                      Next
                    </Button>
                  </Stack>
                </>
              )}

              {dndCreateStep === 'abilities' && (
                <>
                  <Typography variant="body2" color="text.secondary">
                    Step 3: Assign ability scores (point buy)
                  </Typography>
                  <Typography variant="body2" color={dndPointBuyRemaining < 0 ? 'error.main' : 'text.secondary'}>
                    Points remaining: {dndPointBuyRemaining}
                  </Typography>
                  <Stack spacing={1} sx={{ mt: 1 }}>
                    {['Strength', 'Dexterity', 'Constitution', 'Intelligence', 'Wisdom', 'Charisma'].map((a) => (
                      <Paper key={a} variant="outlined" sx={{ p: 1, display: 'flex', alignItems: 'center', gap: 1 }}>
                        <Typography variant="body2" sx={{ flex: 1, fontWeight: 600 }}>
                          {a}
                        </Typography>
                        <Button variant="contained" disabled={!dndCanDec(a)} onClick={() => dndAdjustAbility(a, -1)}>
                          -
                        </Button>
                        <Typography variant="body2" sx={{ width: 32, textAlign: 'center' }}>
                          {dndAbilities[a] ?? 8}
                        </Typography>
                        <Button variant="contained" disabled={!dndCanInc(a)} onClick={() => dndAdjustAbility(a, +1)}>
                          +
                        </Button>
                      </Paper>
                    ))}
                  </Stack>
                  <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1} sx={{ mt: 1 }}>
                    <Button variant="outlined" onClick={() => setDndCreateStep('class')}>
                      Back
                    </Button>
                    <Button variant="outlined" onClick={dndResetAbilities}>
                      Reset
                    </Button>
                    <Button
                      variant="contained"
                      disabled={dndPointBuyRemaining < 0}
                      onClick={() => setDndCreateStep('background')}
                    >
                      Next
                    </Button>
                  </Stack>
                </>
              )}

              {dndCreateStep === 'background' && (
                <>
                  <Typography variant="body2" color="text.secondary">
                    Step 4: Background questions
                  </Typography>
                  <Stack spacing={1} sx={{ mt: 1 }}>
                    {(dndBackgroundQuestions || []).map((q) => {
                      const v = dndBackgroundAnswers[q.id] ?? '';
                      if (q.kind === 'choice') {
                        return (
                          <TextField
                            key={q.id}
                            select
                            label={q.prompt}
                            size="small"
                            value={v}
                            onChange={(e) => setBgAnswer(q.id, String(e.target.value))}
                          >
                            <MenuItem value="">(choose)</MenuItem>
                            {(q.options || []).map((opt) => (
                              <MenuItem key={opt} value={opt}>
                                {opt}
                              </MenuItem>
                            ))}
                          </TextField>
                        );
                      }
                      return (
                        <TextField
                          key={q.id}
                          label={q.prompt}
                          size="small"
                          value={v}
                          onChange={(e) => setBgAnswer(q.id, String(e.target.value))}
                          multiline
                          minRows={2}
                        />
                      );
                    })}
                  </Stack>
                  <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1} sx={{ mt: 1 }}>
                    <Button variant="outlined" onClick={() => setDndCreateStep('abilities')}>
                      Back
                    </Button>
                    <Button variant="contained" onClick={() => setDndCreateStep('confirm')}>
                      Next
                    </Button>
                  </Stack>
                </>
              )}

              {dndCreateStep === 'confirm' && (
                <>
                  <Typography variant="body2" color="text.secondary">
                    Step 5: Confirm &amp; save
                  </Typography>
                  <TextField
                    label="Name (optional)"
                    size="small"
                    value={dndName}
                    onChange={(e) => setDndName(e.target.value)}
                  />
                  <Paper variant="outlined" sx={{ p: 1.25 }}>
                    <Typography variant="body2" sx={{ fontWeight: 600 }}>
                      {dndRace} {dndClass}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      STR {dndAbilities.Strength} · DEX {dndAbilities.Dexterity} · CON {dndAbilities.Constitution}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      INT {dndAbilities.Intelligence} · WIS {dndAbilities.Wisdom} · CHA {dndAbilities.Charisma}
                    </Typography>
                  </Paper>
                  <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1}>
                    <Button variant="outlined" onClick={() => setDndCreateStep('background')}>
                      Back
                    </Button>
                    <Button
                      variant="contained"
                      disabled={!dndRace || !dndClass || dndPointBuyRemaining < 0}
                      onClick={() =>
                        send({
                          type: 'dnd_create_character',
                          name: dndName,
                          race: dndRace,
                          char_class: dndClass,
                          abilities: dndAbilities,
                          background_answers: dndBackgroundAnswers,
                        })
                      }
                    >
                      Save Character
                    </Button>
                  </Stack>
                </>
              )}
            </Stack>
          )}
        </>
      )}

      <DndDicePanel send={send} />
    </>
  );
}
