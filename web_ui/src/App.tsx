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
  LinearProgress,
  Paper,
  Slider,
  Stack,
  TextField,
  Toolbar,
  Typography,
} from '@mui/material';
import PlayingCard from './components/PlayingCard';
import type { Snapshot, SnapshotMessage } from './types';
import PopupDialog from './features/popup/PopupDialog';
import DndCharacterSetup from './features/dnd/DndCharacterSetup';
import DndDmControls from './features/dnd/DndDmControls';
import DndDicePanel from './features/dnd/DndDicePanel';
import BlackjackPanel from './features/blackjack/BlackjackPanel';
import MonopolyPanel from './features/monopoly/MonopolyPanel';
import UnoPanel from './features/uno/UnoPanel';
import ExplodingKittensPanel from './features/exploding_kittens/ExplodingKittensPanel';
import TexasHoldemPanel from './features/texas_holdem/TexasHoldemPanel';
import UnstableUnicornsPanel from './features/unstable_unicorns/UnstableUnicornsPanel';
import CluedoPanel from './features/cluedo/CluedoPanel';
import RiskPanel from './features/risk/RiskPanel';
import CatanPanel from './features/catan/CatanPanel';
import GameBanner, { getGameTheme } from './components/GameBanner';

type ConnStatus = 'disconnected' | 'connecting' | 'connected' | 'error';

export default function App(): React.ReactElement {
  const [playerName, setPlayerName] = useState<string>('');

  const [status, setStatus] = useState<ConnStatus>('disconnected');
  const [statusText, setStatusText] = useState<string>('Not connected');

  const [snapshot, setSnapshot] = useState<Snapshot | null>(null);

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

  const myGameVote =
    isSeated ? (snapshot?.lobby?.players || []).find((p) => p.seat === (mySeat as number))?.vote ?? null : null;

  const normalizeVoteKey = (k?: string | null) => {
    const v = String(k || '').trim().toLowerCase();
    if (v === 'd&d' || v === 'dnd') return 'dnd';
    return v;
  };
  const [showConnect, setShowConnect] = useState<boolean>(true);
  const [isReady, setIsReady] = useState<boolean>(false);

  const inMenu = snapshot?.server_state === 'menu';
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
        // Some browsers require a text type for drag to initiate.
        e.dataTransfer.setData('text/plain', JSON.stringify(payload));
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

  const DND_EQUIP_SLOTS = useMemo(() => ['helmet', 'chest', 'leggings', 'boots', 'sword', 'bow', 'staff', 'knife'], []);

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

  const CardRow = useCallback(
    ({ cards }: { cards: string[] }) => (
      <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
        {(cards || []).map((c, i) => (
          <PlayingCard key={`${c}-${i}`} card={c} size="sm" />
        ))}
      </Stack>
    ),
    []
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

  const audio = snapshot?.audio ?? null;
  // Always show audio controls when there is a snapshot (use safe defaults)
  const showAudio = !!snapshot;
  const audioVolume = audio?.volume ?? 35;
  const audioMuted = audio?.music_muted ?? false;
  const audioVotedMute = audio?.you_voted_mute ?? false;
  const audioMuteVotes = audio?.mute_votes ?? 0;
  const audioMuteRequired = audio?.mute_required ?? 1;
  const voteMuteMusic = useCallback(() => {
    if (!isSeated) return;
    send({ type: 'vote_music_mute' });
  }, [isSeated, send]);

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

            {showAudio && (
              <Paper variant="outlined" sx={{ p: 1.5, mb: 2 }}>
                <Typography variant="subtitle2" sx={{ mb: 1 }}>🎵 Audio</Typography>
                <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1} alignItems="center" sx={{ mb: 1 }}>
                  <Button
                    variant={audioVotedMute ? 'contained' : 'outlined'}
                    color={audioMuted ? 'warning' : 'primary'}
                    onClick={voteMuteMusic}
                    disabled={!isSeated || status !== 'connected'}
                    size="small"
                  >
                    {audioVotedMute ? 'Mute vote ✓' : 'Vote: Mute music'}
                  </Button>
                  <Chip
                    label={`Mute votes: ${audioMuteVotes}/${audioMuteRequired} (${audioMuted ? 'muted' : 'playing'})`}
                    color={audioMuted ? 'warning' : 'default'}
                    variant={audioMuted ? 'filled' : 'outlined'}
                    size="small"
                  />
                </Stack>
                {isSeated && mySeat === 0 && (
                <Stack direction="row" spacing={2} alignItems="center">
                  <Typography variant="body2" sx={{ whiteSpace: 'nowrap' }}>🔊 Vol</Typography>
                  <Slider
                    value={audioVolume}
                    min={0}
                    max={100}
                    step={5}
                    size="small"
                    valueLabelDisplay="auto"
                    disabled={status !== 'connected'}
                    onChange={(_e, v) => send({ type: 'set_volume', volume: v as number })}
                    sx={{ minWidth: 100, flex: 1 }}
                  />
                  <Typography variant="body2" sx={{ whiteSpace: 'nowrap' }}>
                    {audioVolume}%
                  </Typography>
                </Stack>
                )}
              </Paper>
            )}

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
                                            : p.vote === 'uno'
                                              ? 'Uno'
                                              : p.vote === 'catan'
                                                ? 'Catan'
                                              : p.vote === 'exploding_kittens'
                                                ? 'Exploding Kittens'
                                              : p.vote === 'texas_holdem'
                                                ? "Texas Hold'em"
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

            <BlackjackPanel snapshot={snapshot} status={status} isSeated={isSeated} send={send} CardRow={CardRow} />

            <UnoPanel snapshot={snapshot} seatLabel={seatLabel} send={send} playerColors={playerColors} />

            <ExplodingKittensPanel snapshot={snapshot} seatLabel={seatLabel} send={send} playerColors={playerColors} />

            <TexasHoldemPanel snapshot={snapshot} seatLabel={seatLabel} send={send} playerColors={playerColors} />

            <UnstableUnicornsPanel snapshot={snapshot} seatLabel={seatLabel} send={send} playerColors={playerColors} />

            <CluedoPanel snapshot={snapshot} seatLabel={seatLabel} send={send} playerColors={playerColors} />

            <RiskPanel snapshot={snapshot} seatLabel={seatLabel} send={send} playerColors={playerColors} />

            <CatanPanel snapshot={snapshot} seatLabel={seatLabel} send={send} />

            {snapshot.server_state === 'menu' && (
              <>
                <Typography variant="subtitle1" gutterBottom sx={{ fontWeight: 700 }}>
                  🎲 Choose Game — Vote Now
                </Typography>
                {!snapshot.lobby?.all_ready ? (
                  <Typography variant="body2" color="text.secondary">
                    Everyone must be Ready before voting.
                  </Typography>
                ) : (
                  <>
                    <Box
                      sx={{
                        display: 'grid',
                        gridTemplateColumns: { xs: 'repeat(2, 1fr)', sm: 'repeat(3, 1fr)' },
                        gap: 1.5,
                      }}
                    >
                      {(snapshot.menu_games || []).map((g) => {
                        const selected = normalizeVoteKey(myGameVote) === normalizeVoteKey(g.key);
                        const theme = getGameTheme(g.key);
                        const voteCount = (snapshot.lobby?.votes as any)?.[g.key] ?? 0;
                        return (
                          <Box
                            key={g.key}
                            onClick={() =>
                              status === 'connected' && isSeated && isReady
                                ? send({ type: 'vote_game', key: g.key })
                                : undefined
                            }
                            sx={{
                              cursor: status === 'connected' && isSeated && isReady ? 'pointer' : 'default',
                              opacity: status !== 'connected' || !isSeated || !isReady ? 0.5 : 1,
                              borderRadius: 2,
                              overflow: 'hidden',
                              border: selected ? `3px solid ${theme.accentColor}` : '3px solid transparent',
                              boxShadow: selected ? `0 0 14px ${theme.accentColor}99` : 'none',
                              transition: 'all 0.2s ease',
                              animation: 'fadeInUp 0.35s ease-out',
                              '&:hover': status === 'connected' && isSeated && isReady ? { transform: 'translateY(-3px) scale(1.02)', boxShadow: `0 6px 20px ${theme.accentColor}66` } : {},
                              position: 'relative',
                            }}
                          >
                            <GameBanner game={g.key} compact />
                            {voteCount > 0 && (
                              <Box
                                sx={{
                                  position: 'absolute',
                                  top: 6,
                                  right: 6,
                                  background: theme.accentColor,
                                  color: '#fff',
                                  borderRadius: '50%',
                                  width: 22,
                                  height: 22,
                                  display: 'flex',
                                  alignItems: 'center',
                                  justifyContent: 'center',
                                  fontSize: 11,
                                  fontWeight: 700,
                                  boxShadow: '0 1px 4px rgba(0,0,0,0.4)',
                                }}
                              >
                                {voteCount}
                              </Box>
                            )}
                            {selected && (
                              <Box
                                sx={{
                                  position: 'absolute',
                                  bottom: 0,
                                  left: 0,
                                  right: 0,
                                  textAlign: 'center',
                                  background: `${theme.accentColor}cc`,
                                  color: '#fff',
                                  fontSize: 10,
                                  fontWeight: 700,
                                  py: 0.25,
                                  letterSpacing: 1,
                                }}
                              >
                                ✓ YOUR VOTE
                              </Box>
                            )}
                          </Box>
                        );
                      })}
                    </Box>

                    <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block' }}>
                      Majority wins. For 2 players, both must vote the same.
                    </Typography>
                  </>
                )}
              </>
            )}

            {isDnD && dndState === 'char_creation' && (
              <>
                <DndCharacterSetup
                  snapshot={snapshot}
                  isDm={isDm}
                  isSeated={isSeated}
                  myDndRow={myDndRow as any}
                  seatLabel={seatLabel}
                  send={send}
                  dndEmojiForRace={dndEmojiForRace}
                  dndEmojiForClass={dndEmojiForClass}
                />
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

                <DndDicePanel send={send} />

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

                {isDm && <DndDmControls snapshot={snapshot} seatLabel={seatLabel} send={send} />}
              </>
            )}

            <MonopolyPanel snapshot={snapshot} seatLabel={seatLabel} send={send} playerColors={playerColors} />

            <PopupDialog
              snapshot={snapshot}
              send={send}
              seatLabel={seatLabel}
              allowPopupLineColor={allowPopupLineColor}
              isTradePopup={isTradePopup}
              tradePopup={tradePopup}
              isTradeEditable={isTradeEditable}
              tradeMoneyStep={tradeMoneyStep}
              tradeSetMoney={tradeSetMoney}
              tradeSetProperty={tradeSetProperty}
              onPropDragStart={onPropDragStart}
              onTradeDrop={onTradeDrop}
              isTradeSelectPopup={isTradeSelectPopup}
              tradeSelectPopup={tradeSelectPopup}
            />
          </Paper>
        )}
      </Container>
    </Box>
  );
}
