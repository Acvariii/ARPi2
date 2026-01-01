export type CursorSnapshot = {
  player_idx: number;
  name: string;
  color?: [number, number, number];
  x: number; // 0..1
  y: number; // 0..1
  age_ms: number;
};

export type Snapshot = {
  server_state: string;
  history?: string[];
  audio?: {
    music_muted: boolean;
    mute_votes: number;
    mute_required: number;
    you_voted_mute: boolean;
  };
  end_game?: {
    pressed: boolean;
    pressed_count: number;
    required_count: number;
  };
  palette?: {
    player_colors?: string[];
  };
  available_player_slots?: number[];
  taken_player_slots?: number[];
  your_player_slot?: number;
  lobby?: {
    players?: Array<{ client_id: string; seat: number; name: string; ready: boolean; vote?: string | null; connected: boolean }>;
    all_ready?: boolean;
    votes?: Record<string, number>;
    seated_count?: number;
    min_players?: number;
  };
  menu_games?: Array<{ key: string; label: string }>;
  player_select?: {
    slots: Array<{ player_idx: number; label: string; selected: boolean }>;
    start_enabled: boolean;
    dm_player_idx?: number | null;
  };
  dnd?: {
    state: string;
    dm_player_idx?: number | null;
    background?: string | null;
    background_files?: string[];
    background_questions?: Array<{
      id: string;
      kind: 'choice' | 'text';
      prompt: string;
      options?: string[];
    }>;
    in_combat?: boolean;
    races?: string[];
    classes?: string[];
    monsters?: string[];
    enemies?: Array<{ enemy_idx: number; name: string; hp: number; max_hp: number; ac: number; cr: number }>;
    // Inventory items are structured to support use/equip.
    items_schema_v?: number;
    players?: Array<{
      player_idx: number;
      selected: boolean;
      is_dm: boolean;
      has_saved: boolean;
      has_character: boolean;
      name: string;
      race: string;
      char_class: string;
      hp: number;
      ac: number;
      abilities?: Record<string, number>;
      skills?: string[];
      background?: string;
      feats?: string[];
      features?: string[];
      inventory?: Array<{
        id: string;
        name: string;
        kind: 'consumable' | 'gear' | 'misc';
        slot?: string;
        ac_bonus?: number;
        ability_bonuses?: Record<string, number>;
        effect?: { type: string; amount?: number };
      }>;
      equipment?: Record<string, string>;
    }>;
  };
  popup?: {
    active: boolean;
    popup_type?: string;
    lines?: string[];
    line_items?: Array<{ text: string; color?: string | null }>;
    buttons?: Array<{ id: string; text: string; enabled: boolean }>;
    deed_detail?:
      | {
          idx: number;
          name: string;
          type: string;
          group?: string | null;
          color?: string | null;
          price: number;
          mortgage_value: number;
          unmortgage_cost: number;
          house_cost: number;
          rent_tiers?: number[] | null;
          mortgaged: boolean;
          houses: number;
          owned_in_group?: number | null;
          scroll_index?: number | null;
          scroll_total?: number | null;
          player_money?: number | null;
        }
      | null;
    trade?: {
      initiator: number;
      partner: number;
      offer: { money: number; properties: number[] };
      request: { money: number; properties: number[] };
      initiator_assets: {
        money: number;
        properties: Array<{ idx: number; name: string; color?: string | null; mortgaged: boolean; houses: number; tradable: boolean }>;
      };
      partner_assets: {
        money: number;
        properties: Array<{ idx: number; name: string; color?: string | null; mortgaged: boolean; houses: number; tradable: boolean }>;
      };
    } | null;
    trade_select?:
      | {
          initiator: number;
          partner: number;
          partner_name: string;
          choice_index: number;
          choice_count: number;
          partner_assets: {
            money: number;
            properties: Array<{ idx: number; name: string; color?: string | null; mortgaged: boolean; houses: number; tradable: boolean }>;
          };
        }
      | null;
  };
  panel_buttons?: Array<{ id: string; text: string; enabled: boolean }>;
  blackjack?: {
    state?: string;
    phase_text?: string;
    ready_count?: number | null;
    required_count?: number | null;
    your_chips?: number;
    your_current_bet?: number;
    your_total_bet?: number;
    your_hand?: string[];
    your_hand_value?: number | null;
    result_popup?:
      | {
          round_id: number;
          dealer: { cards: string[]; value: number | null; busted: boolean; blackjack: boolean };
          hands: Array<{
            title: string;
            message: string;
            bet: number;
            cards: string[];
            value: number | null;
            busted: boolean;
            blackjack: boolean;
          }>;
        }
      | null;
  };
  monopoly?: {
    current_turn_seat?: number | null;
    current_turn_name?: string | null;
    players?: Array<{
      player_idx: number;
      name: string;
      money: number;
      jail_free_cards?: number;
      properties: Array<{ idx: number; name: string }>;
    }>;
    // property index -> owner player index (stringified keys to match JSON)
    ownership?: Record<string, number>;
  };
  uno?: {
    state?: string;
    active_players?: number[];
    current_turn_seat?: number | null;
    direction?: number;
    current_color?: string | null;
    top_card?: string | null;
    // keys are stringified in JSON
    hand_counts?: Record<string, number>;
    your_hand?: Array<{ idx: number; text: string; playable: boolean }>;
    winner?: number | null;
    awaiting_color?: boolean;
    next_round_ready?: Record<string, boolean>;
    next_round_ready_count?: number;
    next_round_total?: number;
  };
  exploding_kittens?: {
    state?: string;
    active_players?: number[];
    eliminated_players?: number[];
    current_turn_seat?: number | null;
    pending_draws?: number;
    deck_count?: number;
    discard_top?: string | null;
    last_event?: string | null;
    last_event_age_ms?: number;
    // keys are stringified in JSON
    hand_counts?: Record<string, number>;
    your_hand?: Array<{ idx: number; text: string; playable: boolean }>;
    awaiting_favor_target?: boolean;
    nope_active?: boolean;
    nope_count?: number;
    winner?: number | null;
  };
  texas_holdem?: {
    state?: string;
    street?: string;
    hand_id?: number;
    dealer_seat?: number | null;
    turn_seat?: number | null;
    pot?: number;
    current_bet?: number;
    call_amount?: number | null;
    community?: string[];
    your_hole?: string[];
    // keys are stringified in JSON
    revealed_holes?: Record<string, string[]>;
    players?: Array<{ seat: number; name: string; stack: number; status: string; bet: number }>;
    showdown?: {
      winners?: number[];
      descriptions?: Record<string, string>;
      pot?: number;
      reason?: string;
    } | null;
  };
  unstable_unicorns?: {
    state?: string;
    active_players?: number[];
    current_turn_seat?: number | null;
    turn_phase?: string;
    action_taken?: boolean;
    deck_count?: number;
    discard_count?: number;
    goal_unicorns?: number;
    winner?: number | null;
    your_hand?: Array<{ idx: number; id: string; name: string; kind: string; emoji?: string; color?: string; playable: boolean }>;
    // keys are stringified in JSON
    stables?: Record<string, Array<{ id: string; name: string; kind: string; emoji?: string; color?: string }>>;
    protected_turns?: Record<string, number>;
    hand_counts?: Record<string, number>;
    reaction?: {
      actor?: number | null;
      card?: { id: string; name: string; kind: string; emoji?: string; color?: string };
      awaiting_seat?: number | null;
      stack?: Array<{ id: string; name: string; kind: string; emoji?: string; color?: string }>;
    } | null;
    prompt?: any;
  };
  cluedo?: {
    game_id?: number;
    state?: string;
    active_players?: number[];
    current_turn_seat?: number | null;
    dice?: [number, number] | null;
    last_roll?: number | null;
    steps_remaining?: number;
    mode?: string;
    winner?: number | null;
    // keys are stringified in JSON
    hand_counts?: Record<string, number>;
    players?: Array<{ seat: number; name: string; eliminated: boolean; room?: string | null; hand_count: number }>;
    your_hand?: Array<{ kind: string; name: string; emoji?: string; text: string }>;
    last_event?: string | null;
    last_event_age_ms?: number;
    private_event?: string | null;
    private_event_age_ms?: number;
  };
  risk?: {
    state?: string;
    active_players?: number[];
    eliminated_players?: number[];
    current_turn_seat?: number | null;
    phase?: string;
    reinforcements_left?: number;
    selected_from?: number | null;
    selected_to?: number | null;
    winner?: number | null;
    last_event?: string | null;
    territories?: Array<{
      tid: number;
      name: string;
      continent: string;
      owner: number | null;
      troops: number;
    }>;
  };
  catan?: {
    state?: string;
    active_players?: number[];
    current_turn_seat?: number | null;
    expansion_mode?: string;
    map_radius?: number;
    ports?: Array<{ q: number; r: number; kind: string }>;
    phase?: string;
    rolled?: boolean;
    pending_build?: string | null;
    your_resources?: Record<string, number> | null;
    robber_tile_idx?: number | null;
    robber_candidates?: number[];
    bank?: Record<string, number>;
    dev?: Record<string, number>;
    knights_played?: number;
    vp?: number;
    largest_army_holder?: number | null;
    longest_road_holder?: number | null;
    winner?: number | null;
    last_event?: string | null;
    last_roll?: number | null;
    tiles?: Array<{ q: number; r: number; kind: string; number: number | null }>;
  };
  cursors?: CursorSnapshot[];
};

export type SnapshotMessage = {
  type: 'snapshot';
  data: Snapshot;
};
