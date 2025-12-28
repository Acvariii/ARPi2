import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  AppBar,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  Container,
  Divider,
  Dialog,
  DialogActions,
  DialogContent,
  LinearProgress,
  MenuItem,
  Paper,
  Stack,
  TextField,
  Toolbar,
  Typography,
} from '@mui/material';
import type { Snapshot, SnapshotMessage } from './types';

type ConnStatus = 'disconnected' | 'connecting' | 'connected' | 'error';

export default function App(): React.ReactElement {
  const [playerName, setPlayerName] = useState<string>('');

  const [status, setStatus] = useState<ConnStatus>('disconnected');
  const [statusText, setStatusText] = useState<string>('Not connected');

  const [snapshot, setSnapshot] = useState<Snapshot | null>(null);

  // D&D Web UI local form state
  const [dndName, setDndName] = useState<string>('');
  const [dndRace, setDndRace] = useState<string>('');
  const [dndClass, setDndClass] = useState<string>('');
  const [dndBackground, setDndBackground] = useState<string>('');
  const [dndBackgroundAnswers, setDndBackgroundAnswers] = useState<Record<string, string>>({});

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
  const [dndMonster, setDndMonster] = useState<string>('');
  const [dndCreateStep, setDndCreateStep] = useState<'race' | 'class' | 'abilities' | 'background' | 'confirm'>('race');
  const [dndAbilities, setDndAbilities] = useState<Record<string, number>>({
    Strength: 8,
    Dexterity: 8,
    Constitution: 8,
    Intelligence: 8,
    Wisdom: 8,
    Charisma: 8,
  });

  const wsRef = useRef<WebSocket | null>(null);

  const wsUrl = useMemo(() => {
    // Always connect to the same host used in the address bar.
    // (When served by the game server, window.location.hostname is the server IP.)
    const h = window.location.hostname || 'localhost';
    return `ws://${h}:8765/ui`;
  }, []);

  const send = useCallback((obj: unknown) => {
    const ws = wsRef.current;
    if (!ws || ws.readyState !== WebSocket.OPEN) return;
    ws.send(JSON.stringify(obj));
  }, []);

  const connect = useCallback(() => {
    try {
      wsRef.current?.close();
    } catch {
      // ignore
    }

    setStatus('connecting');
    setStatusText(`Connecting to ${wsUrl}...`);

    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      setStatus('connected');
      setStatusText('Connected');
      // Seat selection happens after we receive the first snapshot.
      send({ type: 'hello', name: playerName.trim() });
    };

    ws.onmessage = (ev) => {
      try {
        const msg = JSON.parse(String(ev.data)) as SnapshotMessage;
        if (msg && msg.type === 'snapshot') {
          setSnapshot(msg.data);
        }
      } catch {
        // ignore
      }
    };

    ws.onerror = () => {
      setStatus('error');
      setStatusText('Connection error');
    };

    ws.onclose = () => {
      setStatus((s) => (s === 'connected' ? 'disconnected' : s));
      setStatusText('Disconnected');
    };
  }, [playerName, send, wsUrl]);

  const playerColors = useMemo(() => {
    const colors = snapshot?.palette?.player_colors;
    if (colors && colors.length >= 8) return colors;
    return [
      '#ff4d4d',
      '#4d79ff',
      '#4dff88',
      '#ffd24d',
      '#b84dff',
      '#4dfff0',
      '#ff4dd2',
      '#c7ff4d',
    ];
  }, [snapshot?.palette?.player_colors]);

  const mySeat = snapshot?.your_player_slot;
  const isSeated = typeof mySeat === 'number' && mySeat >= 0;
  const [showConnect, setShowConnect] = useState<boolean>(true);
  const [isReady, setIsReady] = useState<boolean>(false);

  const inMenu = snapshot?.server_state === 'menu';
  const inPlayerSelect = !!snapshot?.player_select;
  const inGame = !!snapshot && !inMenu;

  const screenLabel = useMemo(() => {
    const raw = snapshot?.server_state || 'unknown';
    return String(raw)
      .split('_')
      .filter(Boolean)
      .map((w) => (w ? w[0].toUpperCase() + w.slice(1) : ''))
      .join(' ');
  }, [snapshot?.server_state]);

  const allowPopupLineColor = !!snapshot?.popup?.popup_type?.startsWith('trade_');

  const tradePopup = snapshot?.popup?.trade || null;
  const isTradePopup = !!snapshot?.popup?.active && !!tradePopup && typeof tradePopup.initiator === 'number';
  const isTradeEditable =
    isTradePopup && snapshot?.popup?.popup_type === 'trade_web_edit' && isSeated && (mySeat as number) === tradePopup!.initiator;

  const tradeSelectPopup = snapshot?.popup?.trade_select || null;
  const isTradeSelectPopup = !!snapshot?.popup?.active && snapshot?.popup?.popup_type === 'trade_select' && !!tradeSelectPopup;

  const tradeMoneyStep = 50;

  const tradeSetMoney = useCallback(
    (side: 'offer' | 'request', delta: number) => {
      send({ type: 'trade_adjust_money', side, delta });
    },
    [send]
  );

  const tradeSetProperty = useCallback(
    (side: 'offer' | 'request', propIdx: number, included: boolean) => {
      send({ type: 'trade_set_property', side, prop_idx: propIdx, included });
    },
    [send]
  );

  const onPropDragStart = useCallback(
    (e: React.DragEvent, payload: { side: 'offer' | 'request'; propIdx: number; included: boolean }) => {
      try {
        e.dataTransfer.setData('application/json', JSON.stringify(payload));
      } catch {
        // ignore
      }
      e.dataTransfer.effectAllowed = 'move';
    },
    []
  );

  const onTradeDrop = useCallback(
    (e: React.DragEvent, target: { side: 'offer' | 'request'; included: boolean }) => {
      e.preventDefault();
      if (!isTradeEditable) return;
      let data: any = null;
      try {
        const raw = e.dataTransfer.getData('application/json');
        data = raw ? JSON.parse(raw) : null;
      } catch {
        data = null;
      }
      if (!data || (data.side !== 'offer' && data.side !== 'request') || typeof data.propIdx !== 'number') return;
      // Only allow drops within the same side (your props -> offer, their props -> request)
      if (data.side !== target.side) return;
      tradeSetProperty(target.side, data.propIdx, target.included);
    },
    [isTradeEditable, tradeSetProperty]
  );

  // Auto-hide Connect panel once the server has assigned us a seat.
  useEffect(() => {
    if (status === 'connected' && isSeated) {
      setShowConnect(false);
    }
  }, [isSeated, status]);

  // Keep desiredSeat valid as availability changes.
  // (Seat selection is button-based now, so no local desiredSeat state.)

  const seatLabel = useCallback(
    (seat: number) => {
      const isDnD = snapshot?.server_state === 'dnd_creation';
      const dmSeat = typeof snapshot?.dnd?.dm_player_idx === 'number' ? snapshot.dnd.dm_player_idx : null;
      const nameFromLobby = (snapshot?.lobby?.players || []).find((p) => p.seat === seat)?.name?.trim();
      const nameFromMonopoly = (snapshot?.monopoly?.players || []).find((p) => p.player_idx === seat)?.name?.trim();
      const display = nameFromLobby || nameFromMonopoly;
      if (display) {
        return isDnD && typeof dmSeat === 'number' && seat === dmSeat ? `${display} (DM)` : display;
      }
      if (isDnD && typeof dmSeat === 'number' && seat === dmSeat) return 'DM';
      return `Player ${seat + 1}`;
    },
    [snapshot?.dnd?.dm_player_idx, snapshot?.lobby?.players, snapshot?.monopoly?.players, snapshot?.server_state]
  );

  const isDnD = snapshot?.server_state === 'dnd_creation';
  const dndState = snapshot?.dnd?.state || '';
  const dndDmSeat = typeof snapshot?.dnd?.dm_player_idx === 'number' ? (snapshot?.dnd?.dm_player_idx ?? null) : null;
  const isDm = isSeated && typeof dndDmSeat === 'number' && (mySeat as number) === dndDmSeat;
  const myDndRow = useMemo(() => {
    if (!isSeated) return null;
    const rows = snapshot?.dnd?.players || [];
    return rows.find((r) => r.player_idx === (mySeat as number)) || null;
  }, [isSeated, mySeat, snapshot?.dnd?.players]);

  const dndBackgroundQuestions = useMemo(() => {
    const qs = snapshot?.dnd?.background_questions;
    return Array.isArray(qs) ? qs : [];
  }, [snapshot?.dnd?.background_questions]);

  const dndBackgroundQuestionSig = useMemo(() => dndBackgroundQuestions.map((q) => q.id).join('|'), [dndBackgroundQuestions]);

  useEffect(() => {
    if (!isDnD) return;
    setDndBackgroundAnswers({});
  }, [dndBackgroundQuestionSig, isDnD]);

  const setBgAnswer = useCallback((id: string, value: string) => {
    setDndBackgroundAnswers((prev) => ({ ...prev, [id]: value }));
  }, []);

  const DND_EQUIP_SLOTS = useMemo(() => ['helmet', 'chest', 'leggings', 'boots', 'sword', 'bow', 'staff', 'knife'], []);
  const DND_ABILITIES = useMemo(
    () => ['Strength', 'Dexterity', 'Constitution', 'Intelligence', 'Wisdom', 'Charisma'],
    []
  );

  const myDndInventory = useMemo(() => {
    const inv = myDndRow?.inventory || [];
    return Array.isArray(inv) ? inv : [];
  }, [myDndRow?.inventory]);

  const myDndEquipment = useMemo(() => {
    const eq = myDndRow?.equipment || {};
    return eq && typeof eq === 'object' ? (eq as Record<string, string>) : {};
  }, [myDndRow?.equipment]);

  const myDndItemsById = useMemo(() => {
    const m = new Map<string, any>();
    for (const it of myDndInventory as any[]) {
      if (it && typeof it === 'object' && typeof (it as any).id === 'string') {
        m.set((it as any).id, it);
      }
    }
    return m;
  }, [myDndInventory]);

  // Seed race/class defaults when D&D snapshot arrives.
  useEffect(() => {
    if (!isDnD) return;
    const races = snapshot?.dnd?.races || [];
    const classes = snapshot?.dnd?.classes || [];
    if (!dndRace && races.length) setDndRace(races[0]);
    if (!dndClass && classes.length) setDndClass(classes[0]);
  }, [dndClass, dndRace, isDnD, snapshot?.dnd?.classes, snapshot?.dnd?.races]);

  useEffect(() => {
    if (!isDnD) return;
    const ms = snapshot?.dnd?.monsters || [];
    if (!dndMonster && ms.length) setDndMonster(ms[0]);
  }, [dndMonster, isDnD, snapshot?.dnd?.monsters]);

  const dndPointBuyRemaining = useMemo(() => {
    const cost: Record<number, number> = { 8: 0, 9: 1, 10: 2, 11: 3, 12: 4, 13: 5, 14: 7, 15: 9 };
    let spent = 0;
    for (const v of Object.values(dndAbilities)) {
      spent += cost[v] ?? 999;
    }
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

  const dndAdjustAbility = useCallback(
    (ability: string, delta: number) => {
      setDndAbilities((prev) => {
        const v = prev[ability] ?? 8;
        const next = Math.max(8, Math.min(15, v + delta));
        return { ...prev, [ability]: next };
      });
    },
    []
  );

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

  const dndEmojiForRace = useCallback((race: string) => {
    const map: Record<string, string> = {
      Human: '🧑',
      Elf: '🧝',
      Dwarf: '🧔',
      Halfling: '🧑‍🦱',
      Orc: '👹',
      Tiefling: '😈',
    };
    return map[race] || '🧙';
  }, []);

  const dndEmojiForClass = useCallback((klass: string) => {
    const map: Record<string, string> = {
      Fighter: '⚔️',
      Wizard: '🪄',
      Rogue: '🗡️',
      Cleric: '⛪',
      Ranger: '🏹',
      Paladin: '🛡️',
    };
    return map[klass] || '🧙';
  }, []);

  const dndEmojiForMonster = useCallback((name: string) => {
    const map: Record<string, string> = {
      Goblin: '👺',
      Orc: '👹',
      Skeleton: '💀',
      Wolf: '🐺',
      Ogre: '👹',
      Troll: '🧌',
      'Dragon Wyrmling': '🐉',
    };
    return map[name] || '👾';
  }, []);

  useEffect(() => {
    if (!isDnD) return;
    const candidates = (snapshot?.dnd?.players || []).filter((p) => p.selected && !p.is_dm);
    if (!candidates.length) return;
    if (!candidates.some((p) => p.player_idx === dndGiveTarget)) {
      setDndGiveTarget(candidates[0].player_idx);
    }
  }, [dndGiveTarget, isDnD, snapshot?.dnd?.players]);

  const parseCard = useCallback((card: string) => {
    const t = (card || '').trim();
    if (!t) return { rank: '', suit: '', isRed: false };
    const suit = t.slice(-1);
    const rank = t.slice(0, -1);
    const isRed = suit === '♥' || suit === '♦';
    return { rank, suit, isRed };
  }, []);

  const PlayingCardView = useCallback(
    ({ card }: { card: string }) => {
      const c = parseCard(card);
      return (
        <Box
          sx={{
            width: 46,
            height: 64,
            border: 1,
            borderColor: 'divider',
            borderRadius: 1,
            bgcolor: 'background.paper',
            position: 'relative',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            userSelect: 'none',
          }}
        >
          <Typography
            variant="caption"
            sx={{
              position: 'absolute',
              top: 4,
              left: 6,
              fontWeight: 800,
              color: c.isRed ? 'error.main' : 'text.primary',
              lineHeight: 1,
            }}
          >
            {c.rank}
            {c.suit}
          </Typography>
          <Typography
            variant="h6"
            sx={{
              fontWeight: 900,
              color: c.isRed ? 'error.main' : 'text.primary',
              lineHeight: 1,
            }}
          >
            {c.suit}
          </Typography>
        </Box>
      );
    },
    [parseCard]
  );

  const CardRow = useCallback(
    ({ cards }: { cards: string[] }) => (
      <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
        {(cards || []).map((c, i) => (
          <PlayingCardView key={`${c}-${i}`} card={c} />
        ))}
      </Stack>
    ),
    [PlayingCardView]
  );



  const setReady = useCallback(
    (ready: boolean) => {
      setIsReady(ready);
      send({ type: 'set_ready', ready });
    },
    [send]
  );

  const quit = useCallback(() => {
    // Best-effort release seat immediately, then close the socket.
    send({ type: 'quit' });
    try {
      wsRef.current?.close();
    } catch {
      // ignore
    }
    setIsReady(false);
    setShowConnect(true);
  }, [send]);

  const endGamePressed = !!snapshot?.end_game?.pressed;
  const endGamePressedCount = snapshot?.end_game?.pressed_count ?? 0;
  const endGameRequiredCount = snapshot?.end_game?.required_count ?? 0;

  const toggleEndGame = useCallback(() => {
    send({ type: 'end_game', pressed: !endGamePressed });
  }, [endGamePressed, send]);

  // Ready is a menu-only concept; keep local UI in sync when state changes.
  useEffect(() => {
    if (!inMenu) {
      setIsReady(false);
    }
  }, [inMenu]);

  useEffect(() => {
    return () => {
      try {
        wsRef.current?.close();
      } catch {
        // ignore
      }
    };
  }, []);

  const chipColor = status === 'connected' ? 'success' : status === 'error' ? 'error' : 'default';

  const lobbyPhaseLabel = useMemo(() => {
    const seated = snapshot?.lobby?.seated_count;
    const min = snapshot?.lobby?.min_players;
    const allReady = !!snapshot?.lobby?.all_ready;
    if (typeof seated === 'number' && typeof min === 'number' && seated < min) {
      return `Waiting for players (${seated}/${min})`;
    }
    if (!allReady) return 'Waiting for players to Ready';
    return 'Selecting game (vote now)';
  }, [snapshot?.lobby?.all_ready, snapshot?.lobby?.min_players, snapshot?.lobby?.seated_count]);

  return (
    <Box sx={{ minHeight: '100vh' }}>
      <AppBar position="static">
        <Toolbar>
          <Typography variant="h6" sx={{ flexGrow: 1 }}>
            ARPi2 Controller
          </Typography>
          <Chip label={statusText} color={chipColor as any} size="small" />
        </Toolbar>
      </AppBar>

      <Container maxWidth="sm" sx={{ py: 2 }}>
        {showConnect && (!snapshot || inMenu) && (
        <Paper sx={{ p: 2, mb: 2 }}>
          <Typography variant="h6" gutterBottom>
            Connect
          </Typography>

          <Stack spacing={2}>
            <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2}>
              <TextField
                label="Name"
                value={playerName}
                onChange={(e) => setPlayerName(e.target.value.slice(0, 24))}
                placeholder="Alex"
                fullWidth
              />
            </Stack>

            {status === 'connected' && snapshot && !isSeated && (
              <Typography variant="body2" color="text.secondary">
                Assigning your seat…
              </Typography>
            )}

            <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1}>
              <Button variant="contained" onClick={connect} disabled={status === 'connecting'}>
                {status === 'connected' ? 'Reconnect' : 'Connect'}
              </Button>
            </Stack>
          </Stack>
        </Paper>
        )}

        {snapshot && (
          <Paper sx={{ p: 2 }}>
            <Typography variant="h6" gutterBottom>
              Screen: {screenLabel}
            </Typography>

            <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
              Seat: {isSeated ? seatLabel(mySeat as number) : 'No seat selected'}
            </Typography>

            {inMenu && (
              <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1} sx={{ mb: 2 }}>
                <Button
                  variant={isReady ? 'contained' : 'outlined'}
                  color={isReady ? 'success' : 'primary'}
                  onClick={() => setReady(!isReady)}
                  disabled={!isSeated || status !== 'connected'}
                >
                  {isReady ? 'Ready ✓' : 'Ready'}
                </Button>
                <Chip
                  label={
                    snapshot.lobby?.seated_count !== undefined && snapshot.lobby?.min_players !== undefined &&
                    snapshot.lobby.seated_count < snapshot.lobby.min_players
                      ? `Need ${snapshot.lobby.min_players} players connected (${snapshot.lobby.seated_count}/${snapshot.lobby.min_players})`
                      : snapshot.lobby?.all_ready
                        ? 'All players ready'
                        : 'Waiting for players to ready up'
                  }
                  color={snapshot.lobby?.all_ready ? 'success' : 'default'}
                  variant={snapshot.lobby?.all_ready ? 'filled' : 'outlined'}
                  size="small"
                />
              </Stack>
            )}

            {inMenu && (
              <>
                <Typography variant="subtitle1" gutterBottom>
                  Lobby
                </Typography>
                <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                  {lobbyPhaseLabel}
                </Typography>
                <Stack spacing={1} sx={{ mb: 2 }}>
                  {(snapshot.lobby?.players || []).length ? (
                    (snapshot.lobby?.players || [])
                      .slice()
                      .sort((a, b) => a.seat - b.seat)
                      .map((p) => (
                        <Paper
                          key={p.client_id}
                          variant="outlined"
                          sx={{
                            p: 1.25,
                            borderColor: playerColors[p.seat % playerColors.length],
                          }}
                        >
                          <Stack direction="row" spacing={1} alignItems="center" sx={{ flexWrap: 'wrap' }}>
                            <Typography variant="body2" sx={{ fontWeight: 600 }}>
                              {seatLabel(p.seat)}
                            </Typography>
                            {!p.connected && <Chip label="Disconnected" size="small" variant="outlined" />}
                            <Chip
                              label={p.ready ? 'Ready' : 'Not ready'}
                              size="small"
                              color={p.ready ? 'success' : 'default'}
                              variant={p.ready ? 'filled' : 'outlined'}
                            />
                            {snapshot.lobby?.all_ready && (
                              <Chip
                                label={
                                  p.vote
                                    ? `Voted: ${
                                        p.vote === 'monopoly'
                                          ? 'Monopoly'
                                          : p.vote === 'blackjack'
                                            ? 'Blackjack'
                                            : p.vote === 'dnd' || p.vote === 'd&d'
                                              ? 'D&D'
                                              : p.vote
                                      }`
                                    : 'No vote'
                                }
                                size="small"
                                variant={p.vote ? 'filled' : 'outlined'}
                                color={p.vote ? 'primary' : 'default'}
                              />
                            )}
                          </Stack>
                        </Paper>
                      ))
                  ) : (
                    <Typography variant="body2" color="text.secondary">
                      No players seated yet.
                    </Typography>
                  )}
                </Stack>
              </>
            )}

            {inGame && (
              <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1} sx={{ mb: 2 }}>
                <Button variant="contained" color="error" onClick={quit} disabled={status !== 'connected'}>
                  Quit
                </Button>
                <Button
                  variant={endGamePressed ? 'contained' : 'outlined'}
                  color={endGamePressed ? 'warning' : 'primary'}
                  onClick={toggleEndGame}
                  disabled={status !== 'connected' || !isSeated}
                >
                  End Game{endGameRequiredCount > 0 ? ` (${endGamePressedCount}/${endGameRequiredCount})` : ''}
                </Button>
              </Stack>
            )}

            {snapshot.server_state === 'blackjack' && snapshot.blackjack && (
              <Paper variant="outlined" sx={{ p: 1.5, mb: 2 }}>
                <Stack spacing={1}>
                  <Typography variant="subtitle1">Blackjack</Typography>
                  <Typography variant="body2" color="text.secondary">
                    Chips: {typeof snapshot.blackjack.your_chips === 'number' ? `$${snapshot.blackjack.your_chips}` : '—'}
                    {' · '}Bet: ${snapshot.blackjack.your_total_bet ?? 0}
                  </Typography>

                  {!!snapshot.blackjack.phase_text && (
                    <Typography variant="body2" color="text.secondary">
                      {snapshot.blackjack.phase_text}
                      {typeof snapshot.blackjack.ready_count === 'number' && typeof snapshot.blackjack.required_count === 'number'
                        ? ` (${snapshot.blackjack.ready_count}/${snapshot.blackjack.required_count})`
                        : ''}
                    </Typography>
                  )}

                  {snapshot.blackjack.state === 'betting' && (
                    <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1}>
                      <Button
                        variant="outlined"
                        onClick={() => send({ type: 'blackjack_adjust_bet', amount: 5 })}
                        disabled={status !== 'connected' || !isSeated || (snapshot.blackjack.your_current_bet ?? 0) < 5}
                      >
                        -$5
                      </Button>
                      <Button
                        variant="outlined"
                        onClick={() => send({ type: 'blackjack_adjust_bet', amount: 25 })}
                        disabled={status !== 'connected' || !isSeated || (snapshot.blackjack.your_current_bet ?? 0) < 25}
                      >
                        -$25
                      </Button>
                      <Button
                        variant="outlined"
                        onClick={() => send({ type: 'blackjack_adjust_bet', amount: snapshot.blackjack?.your_current_bet ?? 0 })}
                        disabled={
                          status !== 'connected' ||
                          !isSeated ||
                          !(snapshot.blackjack?.your_current_bet && snapshot.blackjack.your_current_bet > 0)
                        }
                      >
                        Clear bet
                      </Button>
                    </Stack>
                  )}

                  <Typography variant="body2" sx={{ fontWeight: 600 }}>
                    Your hand{typeof snapshot.blackjack.your_hand_value === 'number' ? ` (value ${snapshot.blackjack.your_hand_value})` : ''}
                  </Typography>
                  {(snapshot.blackjack.your_hand || []).length ? (
                    <CardRow cards={snapshot.blackjack.your_hand || []} />
                  ) : (
                    <Typography variant="body2" color="text.secondary">
                      No cards yet.
                    </Typography>
                  )}
                </Stack>
              </Paper>
            )}

            <Dialog
              open={!!snapshot.blackjack?.result_popup}
              disableEscapeKeyDown
              onClose={(_, reason) => {
                if (reason === 'backdropClick' || reason === 'escapeKeyDown') return;
              }}
            >
              <DialogContent dividers>
                {snapshot.blackjack?.result_popup && (
                  <Stack spacing={1.5}>
                    <Typography variant="subtitle1" sx={{ fontWeight: 800 }}>
                      Round Result
                    </Typography>

                    <Typography variant="body2" color="text.secondary">
                      Dealer{typeof snapshot.blackjack.result_popup.dealer.value === 'number' ? ` (value ${snapshot.blackjack.result_popup.dealer.value})` : ''}
                    </Typography>
                    <CardRow cards={snapshot.blackjack.result_popup.dealer.cards || []} />

                    <Divider />

                    {(snapshot.blackjack.result_popup.hands || []).map((h, idx) => (
                      <Card key={idx} variant="outlined">
                        <CardContent sx={{ py: 1.25, '&:last-child': { pb: 1.25 } }}>
                          <Stack spacing={1}>
                            <Stack direction="row" justifyContent="space-between" alignItems="center">
                              <Typography variant="body2" sx={{ fontWeight: 800 }}>
                                {h.title}
                              </Typography>
                              <Typography variant="caption" color="text.secondary">
                                Bet ${h.bet}
                              </Typography>
                            </Stack>
                            <Typography variant="body2" color="text.secondary">
                              {h.message}
                              {typeof h.value === 'number' ? ` (value ${h.value})` : ''}
                            </Typography>
                            <CardRow cards={h.cards || []} />
                          </Stack>
                        </CardContent>
                      </Card>
                    ))}

                    <Typography variant="caption" color="text.secondary">
                      You must close this popup.
                    </Typography>
                  </Stack>
                )}
              </DialogContent>
              <DialogActions>
                <Button
                  variant="contained"
                  onClick={() => send({ type: 'blackjack_close_result' })}
                  disabled={status !== 'connected' || !isSeated}
                >
                  Close
                </Button>
              </DialogActions>
            </Dialog>

            {snapshot.server_state === 'menu' && (
              <>
                <Typography variant="subtitle1" gutterBottom>
                  Choose Game (Vote)
                </Typography>
                {!snapshot.lobby?.all_ready ? (
                  <Typography variant="body2" color="text.secondary">
                    Everyone must be Ready before voting.
                  </Typography>
                ) : (
                  <>
                    <Stack spacing={1}>
                      {(snapshot.menu_games || []).map((g) => (
                        <Button
                          key={g.key}
                          variant="outlined"
                          onClick={() => send({ type: 'vote_game', key: g.key })}
                          disabled={status !== 'connected' || !isSeated || !isReady}
                        >
                          Vote: {g.label}
                        </Button>
                      ))}
                    </Stack>

                    <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                      Votes: Monopoly {snapshot.lobby?.votes?.monopoly ?? 0} · Blackjack{' '}
                      {snapshot.lobby?.votes?.blackjack ?? 0} · D&D{' '}
                      {(snapshot.lobby?.votes?.['d&d'] ?? 0) + (snapshot.lobby?.votes?.dnd ?? 0)}
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      Majority wins. For 2 players, both must vote the same.
                    </Typography>
                  </>
                )}
              </>
            )}

            {snapshot.player_select && (
              <>
                <Typography variant="subtitle1" gutterBottom sx={{ mt: 2 }}>
                  Player Selection
                </Typography>

                {isDnD && (
                  <>
                    <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                      DM: {typeof dndDmSeat === 'number' ? seatLabel(dndDmSeat) : 'Not set'}
                    </Typography>
                    <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1} sx={{ mb: 1 }}>
                      <Button
                        variant="contained"
                        disabled={!isSeated || isDm}
                        onClick={() => send({ type: 'dnd_set_dm' })}
                      >
                        {isDm ? 'You are DM' : 'Set Me as DM'}
                      </Button>
                    </Stack>
                  </>
                )}

                <Stack spacing={1}>
                  {snapshot.player_select.slots.map((s) => (
                    <Box key={s.player_idx} sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                      <Chip
                        label={s.selected ? 'Selected' : 'Not selected'}
                        color={s.selected ? 'success' : 'default'}
                        size="small"
                        variant={s.selected ? 'filled' : 'outlined'}
                      />
                      <Typography variant="body2">{s.label}</Typography>
                    </Box>
                  ))}
                </Stack>

                <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1} sx={{ mt: 2 }}>
                  <Button
                    variant="contained"
                    disabled={!snapshot.player_select.start_enabled}
                    onClick={() => send({ type: 'start_game' })}
                  >
                    {snapshot.player_select.start_enabled
                      ? 'Start Game'
                      : isDnD
                        ? 'Start (choose DM + 2 players)'
                        : 'Start (need more players)'}
                  </Button>
                </Stack>
              </>
            )}

            {isDnD && dndState === 'char_creation' && (
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
                                  <Button
                                    variant="contained"
                                    disabled={!dndCanDec(a)}
                                    onClick={() => dndAdjustAbility(a, -1)}
                                  >
                                    -
                                  </Button>
                                  <Typography variant="body2" sx={{ width: 32, textAlign: 'center' }}>
                                    {dndAbilities[a] ?? 8}
                                  </Typography>
                                  <Button
                                    variant="contained"
                                    disabled={!dndCanInc(a)}
                                    onClick={() => dndAdjustAbility(a, +1)}
                                  >
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

                <Typography variant="subtitle2" sx={{ mt: 2 }}>
                  Dice
                </Typography>
                <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1} sx={{ mt: 1 }}>
                  {[4, 6, 8, 10, 12, 20].map((sides) => (
                    <Button key={sides} variant="contained" onClick={() => send({ type: 'dnd_roll_dice', sides })}>
                      d{sides}
                    </Button>
                  ))}
                </Stack>
              </>
            )}

            {isDnD && (dndState === 'gameplay' || dndState === 'combat') && (
              <>
                <Typography variant="subtitle1" gutterBottom sx={{ mt: 2 }}>
                  D&amp;D
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  DM: {typeof dndDmSeat === 'number' ? seatLabel(dndDmSeat) : 'Not set'}
                  {snapshot.dnd?.background ? ` · Background: ${snapshot.dnd.background}` : ''}
                </Typography>

                {!!(snapshot.dnd?.enemies || []).length && (
                  <>
                    <Typography variant="subtitle2" sx={{ mt: 2 }}>
                      Encounter
                    </Typography>
                    <Stack spacing={1} sx={{ mt: 1 }}>
                      {(snapshot.dnd?.enemies || []).map((e) => {
                        const pct = e.max_hp > 0 ? Math.max(0, Math.min(100, (e.hp / e.max_hp) * 100)) : 0;
                        return (
                          <Card key={e.enemy_idx} variant="outlined">
                            <CardContent>
                              <Stack direction="row" spacing={1} alignItems="center">
                                <Typography variant="h4">{dndEmojiForMonster(e.name)}</Typography>
                                <Box sx={{ flex: 1 }}>
                                  <Typography variant="body2" sx={{ fontWeight: 700 }}>
                                    {e.name}
                                  </Typography>
                                  <Typography variant="body2" color="text.secondary">
                                    HP {e.hp}/{e.max_hp} · AC {e.ac} · CR {e.cr}
                                  </Typography>
                                  <LinearProgress variant="determinate" value={pct} sx={{ mt: 0.75 }} />
                                </Box>
                              </Stack>

                              {isDm && (
                                <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1} sx={{ mt: 1 }}>
                                  <Button
                                    size="small"
                                    variant="outlined"
                                    onClick={() => send({ type: 'dnd_dm_adjust_enemy_hp', enemy_idx: e.enemy_idx, delta: -5 })}
                                  >
                                    -5
                                  </Button>
                                  <Button
                                    size="small"
                                    variant="outlined"
                                    onClick={() => send({ type: 'dnd_dm_adjust_enemy_hp', enemy_idx: e.enemy_idx, delta: -1 })}
                                  >
                                    -1
                                  </Button>
                                  <Button
                                    size="small"
                                    variant="outlined"
                                    onClick={() => send({ type: 'dnd_dm_adjust_enemy_hp', enemy_idx: e.enemy_idx, delta: +1 })}
                                  >
                                    +1
                                  </Button>
                                  <Button
                                    size="small"
                                    variant="outlined"
                                    onClick={() => send({ type: 'dnd_dm_adjust_enemy_hp', enemy_idx: e.enemy_idx, delta: +5 })}
                                  >
                                    +5
                                  </Button>
                                  <Button
                                    size="small"
                                    variant="contained"
                                    onClick={() => send({ type: 'dnd_dm_remove_enemy', enemy_idx: e.enemy_idx })}
                                  >
                                    Remove
                                  </Button>
                                </Stack>
                              )}
                            </CardContent>
                          </Card>
                        );
                      })}
                    </Stack>
                  </>
                )}

                <Typography variant="subtitle2" sx={{ mt: 2 }}>
                  Dice
                </Typography>
                <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1} sx={{ mt: 1 }}>
                  {[4, 6, 8, 10, 12, 20].map((sides) => (
                    <Button key={sides} variant="contained" onClick={() => send({ type: 'dnd_roll_dice', sides })}>
                      d{sides}
                    </Button>
                  ))}
                </Stack>

                {!!myDndRow?.has_character && (
                  <>
                    <Typography variant="subtitle2" sx={{ mt: 2 }}>
                      Your Gear &amp; Items
                    </Typography>
                    <Card variant="outlined" sx={{ mt: 1 }}>
                      <CardContent>
                        <Typography variant="body2" color="text.secondary">
                          HP {myDndRow.hp} · AC {myDndRow.ac}
                        </Typography>

                        <Typography variant="subtitle2" sx={{ mt: 1 }}>
                          Equipment
                        </Typography>
                        <Stack spacing={1} sx={{ mt: 1 }}>
                          {DND_EQUIP_SLOTS.map((slot) => {
                            const itemId = myDndEquipment[slot];
                            const it = itemId ? myDndItemsById.get(itemId) : null;
                            return (
                              <Paper key={slot} variant="outlined" sx={{ p: 1 }}>
                                <Stack direction="row" spacing={1} alignItems="center">
                                  <Typography variant="body2" sx={{ fontWeight: 700, minWidth: 90 }}>
                                    {slot}
                                  </Typography>
                                  <Typography variant="body2" sx={{ flex: 1 }}>
                                    {it?.name || '—'}
                                  </Typography>
                                  <Button
                                    size="small"
                                    variant="outlined"
                                    disabled={!itemId}
                                    onClick={() => send({ type: 'dnd_unequip_slot', slot })}
                                  >
                                    Unequip
                                  </Button>
                                </Stack>
                              </Paper>
                            );
                          })}
                        </Stack>

                        <Typography variant="subtitle2" sx={{ mt: 2 }}>
                          Inventory
                        </Typography>
                        {!myDndInventory.length && (
                          <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                            No items.
                          </Typography>
                        )}
                        {!!myDndInventory.length && (
                          <Stack spacing={1} sx={{ mt: 1 }}>
                            {(myDndInventory as any[]).map((it) => (
                              <Paper key={it.id} variant="outlined" sx={{ p: 1 }}>
                                <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1} alignItems={{ sm: 'center' }}>
                                  <Box sx={{ flex: 1 }}>
                                    <Typography variant="body2" sx={{ fontWeight: 700 }}>
                                      {it.name}
                                    </Typography>
                                    <Typography variant="body2" color="text.secondary">
                                      {it.kind}
                                      {it.kind === 'gear' && it.slot ? ` · slot: ${it.slot}` : ''}
                                      {it.kind === 'gear' && typeof it.ac_bonus === 'number' && it.ac_bonus !== 0
                                        ? ` · AC +${it.ac_bonus}`
                                        : ''}
                                      {it.kind === 'consumable' && it.effect?.type === 'heal' && it.effect?.amount
                                        ? ` · heals ${it.effect.amount}`
                                        : ''}
                                    </Typography>
                                  </Box>

                                  {it.kind === 'consumable' && (
                                    <Button
                                      size="small"
                                      variant="contained"
                                      onClick={() => send({ type: 'dnd_use_item', item_id: it.id })}
                                    >
                                      Use
                                    </Button>
                                  )}
                                  {it.kind === 'gear' && (
                                    <Button
                                      size="small"
                                      variant="contained"
                                      onClick={() => send({ type: 'dnd_equip_item', item_id: it.id })}
                                    >
                                      Equip
                                    </Button>
                                  )}
                                </Stack>
                              </Paper>
                            ))}
                          </Stack>
                        )}
                      </CardContent>
                    </Card>
                  </>
                )}

                {isDm && (
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
                            <Button
                              variant="contained"
                              disabled={!dndMonster}
                              onClick={() => send({ type: 'dnd_dm_spawn_enemy', monster: dndMonster })}
                            >
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

                              <TextField
                                label="Item name"
                                size="small"
                                value={dndItemName}
                                onChange={(e) => setDndItemName(e.target.value)}
                                placeholder="e.g., Healing Potion"
                                fullWidth
                              />
                            </Stack>

                            {dndItemKind === 'consumable' && (
                              <TextField
                                label="Heal amount"
                                size="small"
                                type="number"
                                value={String(dndConsumableHeal)}
                                onChange={(e) => setDndConsumableHeal(Number(e.target.value || 0))}
                                sx={{ maxWidth: 220 }}
                              />
                            )}

                            {dndItemKind === 'gear' && (
                              <>
                                <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1} alignItems={{ sm: 'center' }}>
                                  <TextField
                                    label="Slot"
                                    size="small"
                                    select
                                    value={dndGearSlot}
                                    onChange={(e) => setDndGearSlot(e.target.value)}
                                    sx={{ minWidth: 180 }}
                                  >
                                    {DND_EQUIP_SLOTS.map((s) => (
                                      <MenuItem key={s} value={s}>
                                        {s}
                                      </MenuItem>
                                    ))}
                                  </TextField>
                                  <TextField
                                    label="AC bonus"
                                    size="small"
                                    type="number"
                                    value={String(dndGearAcBonus)}
                                    onChange={(e) => setDndGearAcBonus(Number(e.target.value || 0))}
                                    sx={{ maxWidth: 220 }}
                                  />
                                </Stack>
                                <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1} flexWrap="wrap" useFlexGap>
                                  {DND_ABILITIES.map((a) => (
                                    <TextField
                                      key={a}
                                      label={a}
                                      size="small"
                                      type="number"
                                      value={String(dndGearBonuses[a] ?? 0)}
                                      onChange={(e) =>
                                        setDndGearBonuses((prev) => ({ ...prev, [a]: Number(e.target.value || 0) }))
                                      }
                                      sx={{ width: 160 }}
                                    />
                                  ))}
                                </Stack>
                              </>
                            )}

                            <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1}>
                              <Button
                                variant="contained"
                                disabled={!dndItemName.trim()}
                                onClick={() => {
                                  const name = dndItemName.trim();
                                  const kind = dndItemKind;
                                  let item: any = { name, kind };
                                  if (kind === 'consumable') {
                                    item = { name, kind, effect: { type: 'heal', amount: Number(dndConsumableHeal || 0) } };
                                  }
                                  if (kind === 'gear') {
                                    const ability_bonuses: Record<string, number> = {};
                                    for (const a of DND_ABILITIES) {
                                      const v = Number(dndGearBonuses[a] || 0);
                                      if (v) ability_bonuses[a] = v;
                                    }
                                    item = {
                                      name,
                                      kind,
                                      slot: dndGearSlot,
                                      ac_bonus: Number(dndGearAcBonus || 0),
                                      ...(Object.keys(ability_bonuses).length ? { ability_bonuses } : {}),
                                    };
                                  }
                                  send({ type: 'dnd_dm_give_item', target_player_idx: dndGiveTarget, item });
                                  setDndItemName('');
                                }}
                              >
                                Give
                              </Button>
                              <Button
                                variant="outlined"
                                onClick={() => {
                                  setDndItemName('');
                                  setDndGearAcBonus(0);
                                  setDndConsumableHeal(5);
                                  setDndGearBonuses({
                                    Strength: 0,
                                    Dexterity: 0,
                                    Constitution: 0,
                                    Intelligence: 0,
                                    Wisdom: 0,
                                    Charisma: 0,
                                  });
                                }}
                              >
                                Reset
                              </Button>
                            </Stack>
                          </Stack>
                        </CardContent>
                      </Card>
                    </Stack>
                  </>
                )}
              </>
            )}

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
                    {snapshot.history.slice().reverse().map((h, i) => (
                      <Typography key={i} variant="body2" color="text.secondary">
                        {h}
                      </Typography>
                    ))}
                  </Stack>
                </Paper>
              </Box>
            )}

            <Dialog open={!!snapshot.popup?.active}>
              <DialogContent dividers>
                {isTradePopup ? (
                  <Stack spacing={2}>
                    <Typography variant="subtitle1" sx={{ fontWeight: 700 }}>
                      Trade: {seatLabel(tradePopup!.initiator)} ↔ {seatLabel(tradePopup!.partner)}
                    </Typography>

                    <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2}>
                      <Card variant="outlined" sx={{ flex: 1 }}>
                        <CardContent>
                          <Typography variant="body2" sx={{ fontWeight: 700, mb: 1 }}>
                            You give
                          </Typography>
                          <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 1, flexWrap: 'wrap' }}>
                            <Typography variant="body2">${tradePopup!.offer.money}</Typography>
                            {isTradeEditable && (
                              <>
                                <Button size="small" variant="outlined" onClick={() => tradeSetMoney('offer', -tradeMoneyStep)}>
                                  -${tradeMoneyStep}
                                </Button>
                                <Button size="small" variant="outlined" onClick={() => tradeSetMoney('offer', +tradeMoneyStep)}>
                                  +${tradeMoneyStep}
                                </Button>
                                <Typography variant="caption" color="text.secondary">
                                  (max ${tradePopup!.initiator_assets.money})
                                </Typography>
                              </>
                            )}
                          </Stack>

                          <Paper
                            variant="outlined"
                            sx={{ p: 1, minHeight: 72 }}
                            onDragOver={(e) => isTradeEditable && e.preventDefault()}
                            onDrop={(e) => onTradeDrop(e, { side: 'offer', included: true })}
                          >
                            <Stack spacing={1}>
                              {(tradePopup!.offer.properties || []).length ? (
                                tradePopup!.offer.properties.map((idx) => {
                                  const p = tradePopup!.initiator_assets.properties.find((pp) => pp.idx === idx);
                                  if (!p) return null;
                                  return (
                                    <Card
                                      key={`offer-${p.idx}`}
                                      variant="outlined"
                                      draggable={isTradeEditable && p.tradable}
                                      onDragStart={(e) => onPropDragStart(e, { side: 'offer', propIdx: p.idx, included: true })}
                                      sx={{ borderColor: p.color || 'divider', opacity: p.tradable ? 1 : 0.6 }}
                                    >
                                      <CardContent sx={{ py: 1, '&:last-child': { pb: 1 } }}>
                                        <Typography variant="body2">{p.name}</Typography>
                                        {!p.tradable && (
                                          <Typography variant="caption" color="text.secondary">
                                            {p.mortgaged ? 'Mortgaged' : p.houses > 0 ? `Houses: ${p.houses}` : 'Not tradable'}
                                          </Typography>
                                        )}
                                      </CardContent>
                                    </Card>
                                  );
                                })
                              ) : (
                                <Typography variant="body2" color="text.secondary">
                                  Drop properties here
                                </Typography>
                              )}
                            </Stack>
                          </Paper>
                        </CardContent>
                      </Card>

                      <Card variant="outlined" sx={{ flex: 1 }}>
                        <CardContent>
                          <Typography variant="body2" sx={{ fontWeight: 700, mb: 1 }}>
                            You get
                          </Typography>
                          <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 1, flexWrap: 'wrap' }}>
                            <Typography variant="body2">${tradePopup!.request.money}</Typography>
                            {isTradeEditable && (
                              <>
                                <Button size="small" variant="outlined" onClick={() => tradeSetMoney('request', -tradeMoneyStep)}>
                                  -${tradeMoneyStep}
                                </Button>
                                <Button size="small" variant="outlined" onClick={() => tradeSetMoney('request', +tradeMoneyStep)}>
                                  +${tradeMoneyStep}
                                </Button>
                                <Typography variant="caption" color="text.secondary">
                                  (max ${tradePopup!.partner_assets.money})
                                </Typography>
                              </>
                            )}
                          </Stack>

                          <Paper
                            variant="outlined"
                            sx={{ p: 1, minHeight: 72 }}
                            onDragOver={(e) => isTradeEditable && e.preventDefault()}
                            onDrop={(e) => onTradeDrop(e, { side: 'request', included: true })}
                          >
                            <Stack spacing={1}>
                              {(tradePopup!.request.properties || []).length ? (
                                tradePopup!.request.properties.map((idx) => {
                                  const p = tradePopup!.partner_assets.properties.find((pp) => pp.idx === idx);
                                  if (!p) return null;
                                  return (
                                    <Card
                                      key={`req-${p.idx}`}
                                      variant="outlined"
                                      draggable={isTradeEditable && p.tradable}
                                      onDragStart={(e) => onPropDragStart(e, { side: 'request', propIdx: p.idx, included: true })}
                                      sx={{ borderColor: p.color || 'divider', opacity: p.tradable ? 1 : 0.6 }}
                                    >
                                      <CardContent sx={{ py: 1, '&:last-child': { pb: 1 } }}>
                                        <Typography variant="body2">{p.name}</Typography>
                                        {!p.tradable && (
                                          <Typography variant="caption" color="text.secondary">
                                            {p.mortgaged ? 'Mortgaged' : p.houses > 0 ? `Houses: ${p.houses}` : 'Not tradable'}
                                          </Typography>
                                        )}
                                      </CardContent>
                                    </Card>
                                  );
                                })
                              ) : (
                                <Typography variant="body2" color="text.secondary">
                                  Drop properties here
                                </Typography>
                              )}
                            </Stack>
                          </Paper>
                        </CardContent>
                      </Card>
                    </Stack>

                    {isTradeEditable && (
                      <>
                        <Divider />
                        <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2}>
                          <Card variant="outlined" sx={{ flex: 1 }}>
                            <CardContent>
                              <Typography variant="body2" sx={{ fontWeight: 700, mb: 1 }}>
                                Your properties
                              </Typography>
                              <Stack spacing={1}>
                                {tradePopup!.initiator_assets.properties.map((p) => {
                                  const selected = tradePopup!.offer.properties.includes(p.idx);
                                  return (
                                    <Card
                                      key={`my-${p.idx}`}
                                      variant="outlined"
                                      draggable={!selected && p.tradable}
                                      onDragStart={(e) => onPropDragStart(e, { side: 'offer', propIdx: p.idx, included: false })}
                                      onDoubleClick={() => p.tradable && tradeSetProperty('offer', p.idx, !selected)}
                                      sx={{
                                        borderColor: p.color || 'divider',
                                        opacity: p.tradable ? 1 : 0.6,
                                        backgroundColor: selected ? 'action.selected' : 'background.paper',
                                        cursor: p.tradable ? 'grab' : 'not-allowed',
                                      }}
                                    >
                                      <CardContent sx={{ py: 1, '&:last-child': { pb: 1 } }}>
                                        <Typography variant="body2">{p.name}</Typography>
                                        {!p.tradable && (
                                          <Typography variant="caption" color="text.secondary">
                                            {p.mortgaged ? 'Mortgaged' : p.houses > 0 ? `Houses: ${p.houses}` : 'Not tradable'}
                                          </Typography>
                                        )}
                                        {selected && (
                                          <Typography variant="caption" color="text.secondary">
                                            In offer (double-click to remove)
                                          </Typography>
                                        )}
                                      </CardContent>
                                    </Card>
                                  );
                                })}
                              </Stack>
                              <Paper
                                variant="outlined"
                                sx={{ mt: 1, p: 1 }}
                                onDragOver={(e) => e.preventDefault()}
                                onDrop={(e) => onTradeDrop(e, { side: 'offer', included: false })}
                              >
                                <Typography variant="caption" color="text.secondary">
                                  Drop here to remove from offer
                                </Typography>
                              </Paper>
                            </CardContent>
                          </Card>

                          <Card variant="outlined" sx={{ flex: 1 }}>
                            <CardContent>
                              <Typography variant="body2" sx={{ fontWeight: 700, mb: 1 }}>
                                Their properties
                              </Typography>
                              <Stack spacing={1}>
                                {tradePopup!.partner_assets.properties.map((p) => {
                                  const selected = tradePopup!.request.properties.includes(p.idx);
                                  return (
                                    <Card
                                      key={`their-${p.idx}`}
                                      variant="outlined"
                                      draggable={!selected && p.tradable}
                                      onDragStart={(e) => onPropDragStart(e, { side: 'request', propIdx: p.idx, included: false })}
                                      onDoubleClick={() => p.tradable && tradeSetProperty('request', p.idx, !selected)}
                                      sx={{
                                        borderColor: p.color || 'divider',
                                        opacity: p.tradable ? 1 : 0.6,
                                        backgroundColor: selected ? 'action.selected' : 'background.paper',
                                        cursor: p.tradable ? 'grab' : 'not-allowed',
                                      }}
                                    >
                                      <CardContent sx={{ py: 1, '&:last-child': { pb: 1 } }}>
                                        <Typography variant="body2">{p.name}</Typography>
                                        {!p.tradable && (
                                          <Typography variant="caption" color="text.secondary">
                                            {p.mortgaged ? 'Mortgaged' : p.houses > 0 ? `Houses: ${p.houses}` : 'Not tradable'}
                                          </Typography>
                                        )}
                                        {selected && (
                                          <Typography variant="caption" color="text.secondary">
                                            In request (double-click to remove)
                                          </Typography>
                                        )}
                                      </CardContent>
                                    </Card>
                                  );
                                })}
                              </Stack>
                              <Paper
                                variant="outlined"
                                sx={{ mt: 1, p: 1 }}
                                onDragOver={(e) => e.preventDefault()}
                                onDrop={(e) => onTradeDrop(e, { side: 'request', included: false })}
                              >
                                <Typography variant="caption" color="text.secondary">
                                  Drop here to remove from request
                                </Typography>
                              </Paper>
                            </CardContent>
                          </Card>
                        </Stack>
                      </>
                    )}
                  </Stack>
                ) : snapshot.popup?.popup_type === 'mortgage' && snapshot.popup?.deed_detail ? (
                  (() => {
                    const deed = snapshot.popup!.deed_detail!;
                    const typeLabel =
                      deed.type === 'property' ? 'Property' : deed.type === 'railroad' ? 'Railroad' : deed.type === 'utility' ? 'Utility' : 'Deed';

                    const statusLabel = deed.mortgaged
                      ? 'Mortgaged'
                      : deed.houses >= 5
                        ? 'Hotel'
                        : deed.houses > 0
                          ? `${deed.houses} House${deed.houses === 1 ? '' : 's'}`
                          : 'Unmortgaged';

                    const rentLines: Array<{ label: string; value: string }> = [];
                    if (deed.type === 'property' && (deed.rent_tiers || []).length) {
                      const tiers = deed.rent_tiers || [];
                      const labels = ['Rent', '1 House', '2 Houses', '3 Houses', '4 Houses', 'Hotel'];
                      for (let i = 0; i < Math.min(labels.length, tiers.length); i++) {
                        rentLines.push({ label: labels[i], value: `$${tiers[i]}` });
                      }
                    } else if (deed.type === 'railroad' && (deed.rent_tiers || []).length) {
                      const tiers = deed.rent_tiers || [];
                      const labels = ['1 Railroad', '2 Railroads', '3 Railroads', '4 Railroads'];
                      for (let i = 0; i < Math.min(labels.length, tiers.length); i++) {
                        rentLines.push({ label: labels[i], value: `$${tiers[i]}` });
                      }
                    }

                    return (
                      <Stack spacing={1.5}>
                        <Card variant="outlined" sx={{ borderColor: deed.color || 'divider' }}>
                          <Box sx={{ height: 10, bgcolor: deed.color || 'divider' }} />
                          <CardContent>
                            <Typography variant="subtitle1" sx={{ fontWeight: 800 }}>
                              {deed.name || `Property #${deed.idx}`}
                            </Typography>

                            <Stack direction="row" spacing={1} alignItems="center" sx={{ flexWrap: 'wrap', mt: 1 }}>
                              <Chip size="small" label={typeLabel} variant="outlined" />
                              <Chip size="small" label={statusLabel} variant="outlined" color={deed.mortgaged ? 'warning' : 'default'} />
                              {typeof deed.scroll_index === 'number' && typeof deed.scroll_total === 'number' && deed.scroll_total > 0 && (
                                <Chip size="small" label={`${deed.scroll_index}/${deed.scroll_total}`} variant="outlined" />
                              )}
                              {typeof deed.owned_in_group === 'number' && deed.owned_in_group > 0 && deed.group && (
                                <Chip size="small" label={`Owned in group: ${deed.owned_in_group}`} variant="outlined" />
                              )}
                            </Stack>

                            <Divider sx={{ my: 1.5 }} />

                            <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1} sx={{ flexWrap: 'wrap' }}>
                              <Typography variant="body2" color="text.secondary">
                                Price: <Box component="span" sx={{ color: 'text.primary', fontWeight: 700 }}>${deed.price}</Box>
                              </Typography>
                              <Typography variant="body2" color="text.secondary">
                                Mortgage: <Box component="span" sx={{ color: 'text.primary', fontWeight: 700 }}>${deed.mortgage_value}</Box>
                              </Typography>
                              <Typography variant="body2" color="text.secondary">
                                Unmortgage: <Box component="span" sx={{ color: 'text.primary', fontWeight: 700 }}>${deed.unmortgage_cost}</Box>
                              </Typography>
                              {deed.type === 'property' && deed.house_cost > 0 && (
                                <Typography variant="body2" color="text.secondary">
                                  House cost: <Box component="span" sx={{ color: 'text.primary', fontWeight: 700 }}>${deed.house_cost}</Box>
                                </Typography>
                              )}
                            </Stack>

                            {deed.type === 'utility' && (
                              <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                                Rent: 4× dice (1 utility), 10× dice (2 utilities)
                              </Typography>
                            )}

                            {(rentLines.length > 0 || deed.type === 'utility') && <Divider sx={{ my: 1.5 }} />}

                            {rentLines.length > 0 && (
                              <Stack spacing={0.75}>
                                <Typography variant="body2" sx={{ fontWeight: 700 }}>
                                  Rent
                                </Typography>
                                {rentLines.map((r) => (
                                  <Box key={r.label} sx={{ display: 'flex', justifyContent: 'space-between', gap: 2 }}>
                                    <Typography variant="body2" color="text.secondary">
                                      {r.label}
                                    </Typography>
                                    <Typography variant="body2" sx={{ fontWeight: 700 }}>
                                      {r.value}
                                    </Typography>
                                  </Box>
                                ))}
                              </Stack>
                            )}
                          </CardContent>
                        </Card>
                      </Stack>
                    );
                  })()
                ) : isTradeSelectPopup ? (
                  <Stack spacing={1.5}>
                    <Typography variant="subtitle1" sx={{ fontWeight: 800 }}>
                      Select Trade Partner
                    </Typography>

                    <Stack direction="row" spacing={1} alignItems="center" sx={{ flexWrap: 'wrap' }}>
                      <Typography variant="body2" sx={{ fontWeight: 700 }}>
                        {seatLabel(tradeSelectPopup!.partner)}
                      </Typography>
                      <Chip
                        size="small"
                        label={`$${tradeSelectPopup!.partner_assets.money}`}
                        color="success"
                        variant="outlined"
                      />
                      <Chip
                        size="small"
                        label={`${tradeSelectPopup!.choice_index}/${tradeSelectPopup!.choice_count}`}
                        variant="outlined"
                      />
                    </Stack>

                    <Divider />

                    <Typography variant="body2" sx={{ fontWeight: 700 }}>
                      Properties
                    </Typography>

                    {(tradeSelectPopup!.partner_assets.properties || []).length ? (
                      <Stack spacing={1}>
                        {tradeSelectPopup!.partner_assets.properties.map((p) => (
                          <Card key={`tp-${p.idx}`} variant="outlined" sx={{ borderColor: p.color || 'divider' }}>
                            <CardContent sx={{ py: 1, '&:last-child': { pb: 1 } }}>
                              <Typography variant="body2">{p.name || `#${p.idx}`}</Typography>
                              {(p.mortgaged || p.houses > 0) && (
                                <Typography variant="caption" color="text.secondary">
                                  {p.mortgaged ? 'Mortgaged' : p.houses > 0 ? `Houses: ${p.houses}` : ''}
                                </Typography>
                              )}
                            </CardContent>
                          </Card>
                        ))}
                      </Stack>
                    ) : (
                      <Typography variant="body2" color="text.secondary">
                        No properties.
                      </Typography>
                    )}

                    <Typography variant="caption" color="text.secondary">
                      Use ◄/► to change player, Select to continue, or Cancel.
                    </Typography>
                  </Stack>
                ) : (
                  <Stack spacing={1}>
                    {((snapshot.popup?.line_items && snapshot.popup.line_items.length
                      ? snapshot.popup.line_items
                      : (snapshot.popup?.lines || []).map((t) => ({ text: t, color: undefined })))
                    ).map((line, i) => (
                      <Typography
                        key={i}
                        variant="body2"
                        sx={{
                          color: allowPopupLineColor ? line.color || 'text.primary' : 'text.primary',
                          fontWeight: allowPopupLineColor && line.color ? 600 : 400,
                        }}
                      >
                        {line.text}
                      </Typography>
                    ))}
                  </Stack>
                )}
              </DialogContent>
              <DialogActions sx={{ px: 2, pb: 2, pt: 1 }}>
                {snapshot.popup?.popup_type === 'mortgage' && snapshot.popup?.deed_detail ? (
                  (() => {
                    const deed = snapshot.popup!.deed_detail!;
                    const buttons = snapshot.popup?.buttons || [];
                    const leftBtn = buttons.find((b) => b.id === 'popup_0');
                    const midBtn = buttons.find((b) => b.id === 'popup_1');
                    const rightBtn = buttons.find((b) => b.id === 'popup_2');

                    const scrollIndex = typeof deed.scroll_index === 'number' ? deed.scroll_index : null;
                    const scrollTotal = typeof deed.scroll_total === 'number' ? deed.scroll_total : null;
                    const canPrev = !!(scrollIndex && scrollTotal && scrollIndex > 1);
                    const canNext = !!(scrollIndex && scrollTotal && scrollIndex < scrollTotal);

                    const mortgageText = midBtn?.text || (deed.mortgaged ? 'Unmortgage' : 'Mortgage');
                    const mortgageEnabled = !!midBtn?.enabled;

                    return (
                      <Box
                        sx={{
                          width: '100%',
                          display: 'grid',
                          gridTemplateColumns: '1fr 1fr 1fr',
                          gridAutoRows: 'auto',
                          gap: 1,
                          alignItems: 'center',
                        }}
                      >
                        <Box sx={{ justifySelf: 'start' }}>
                          <Button
                            variant="contained"
                            disabled={!canPrev || !leftBtn}
                            onClick={() => leftBtn && send({ type: 'click_button', id: leftBtn.id })}
                            sx={{ minWidth: 56 }}
                          >
                            ◄
                          </Button>
                        </Box>

                        <Box sx={{ justifySelf: 'center' }}>
                          <Button
                            variant="contained"
                            disabled={!mortgageEnabled || !midBtn}
                            onClick={() => midBtn && send({ type: 'click_button', id: midBtn.id })}
                            sx={{ minWidth: 160 }}
                          >
                            {mortgageText}
                          </Button>
                        </Box>

                        <Box sx={{ justifySelf: 'end' }}>
                          <Button
                            variant="contained"
                            disabled={!canNext || !rightBtn}
                            onClick={() => rightBtn && send({ type: 'click_button', id: rightBtn.id })}
                            sx={{ minWidth: 56 }}
                          >
                            ►
                          </Button>
                        </Box>

                        <Box sx={{ gridColumn: '2 / 3', justifySelf: 'center' }}>
                          <Button
                            variant="contained"
                            color="inherit"
                            onClick={() => send({ type: 'click_button', id: 'popup_close' })}
                            sx={{ minWidth: 160 }}
                          >
                            Close
                          </Button>
                        </Box>
                      </Box>
                    );
                  })()
                ) : isTradeSelectPopup ? (
                  (() => {
                    const tradeSelect = snapshot.popup!.trade_select!;
                    const buttons = snapshot.popup?.buttons || [];
                    const leftBtn = buttons.find((b) => b.id === 'popup_0');
                    const selectBtn = buttons.find((b) => b.id === 'popup_1');
                    const rightBtn = buttons.find((b) => b.id === 'popup_2');

                    const canPrev = tradeSelect.choice_index > 1;
                    const canNext = tradeSelect.choice_index < tradeSelect.choice_count;
                    const canSelect = !!selectBtn?.enabled;

                    return (
                      <Box
                        sx={{
                          width: '100%',
                          display: 'grid',
                          gridTemplateColumns: '1fr 1fr 1fr',
                          gridAutoRows: 'auto',
                          gap: 1,
                          alignItems: 'center',
                        }}
                      >
                        <Box sx={{ justifySelf: 'start' }}>
                          <Button
                            variant="contained"
                            disabled={!canPrev || !leftBtn}
                            onClick={() => leftBtn && send({ type: 'click_button', id: leftBtn.id })}
                            sx={{ minWidth: 56 }}
                          >
                            ◄
                          </Button>
                        </Box>

                        <Box sx={{ justifySelf: 'center' }}>
                          <Button
                            variant="contained"
                            disabled={!canSelect || !selectBtn}
                            onClick={() => selectBtn && send({ type: 'click_button', id: selectBtn.id })}
                            sx={{ minWidth: 160 }}
                          >
                            Select
                          </Button>
                        </Box>

                        <Box sx={{ justifySelf: 'end' }}>
                          <Button
                            variant="contained"
                            disabled={!canNext || !rightBtn}
                            onClick={() => rightBtn && send({ type: 'click_button', id: rightBtn.id })}
                            sx={{ minWidth: 56 }}
                          >
                            ►
                          </Button>
                        </Box>

                        <Box sx={{ gridColumn: '2 / 3', justifySelf: 'center' }}>
                          <Button
                            variant="contained"
                            color="inherit"
                            onClick={() => send({ type: 'click_button', id: 'popup_cancel' })}
                            sx={{ minWidth: 160 }}
                          >
                            Cancel
                          </Button>
                        </Box>
                      </Box>
                    );
                  })()
                ) : (
                  <Box
                    sx={{
                      width: '100%',
                      display: 'flex',
                      flexWrap: 'wrap',
                      gap: 1,
                      justifyContent: 'flex-end',
                    }}
                  >
                    {(snapshot.popup?.buttons || []).map((b) => (
                      <Button
                        key={b.id}
                        variant="contained"
                        disabled={!b.enabled}
                        onClick={() => send({ type: 'click_button', id: b.id })}
                        sx={{ flex: '1 1 140px' }}
                      >
                        {b.text}
                      </Button>
                    ))}
                  </Box>
                )}
              </DialogActions>
            </Dialog>
          </Paper>
        )}
      </Container>
    </Box>
  );
}
