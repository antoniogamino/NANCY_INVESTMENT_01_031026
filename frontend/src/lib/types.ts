export type Tone = "positive" | "negative" | "warning" | "neutral";

export interface ScoreComponent {
  key: string;
  label: string;
  score: number;
  raw: number;
  weight: number;
  detail: string;
  data_type: string;
  available: boolean;
  mirrored: boolean;
}

export interface Score {
  score: number;
  base_score: number;
  age_discount: number;
  classification: string;
  tone: Tone;
  components: ScoreComponent[];
  earnings_risk: string;
  disclaimer: string;
}

export interface Decay {
  available: boolean;
  price_transaction?: number;
  price_disclosure?: number;
  price_now?: number;
  move_before_disclosure?: number;
  move_after_disclosure?: number;
  move_total?: number;
  favourable_before?: number;
  favourable_after?: number;
  favourable_total?: number;
  share_captured_before_disclosure?: number | null;
  days_since_disclosure?: number;
  score: number | null;
  label: string;
  tone: Tone;
}

export interface Instrument {
  score: number;
  kind: "equity" | "option";
  nature: string;
  moneyness?: string | null;
  days_to_expiry?: number;
  detail: string;
}

export interface TradeAnalysis {
  id: number;
  ticker: string;
  company: string;
  asset: string;
  sector: string | null;
  transaction_type: "BUY" | "SELL" | "EXERCISE";
  asset_type: string;
  transaction_date: string;
  disclosure_date: string;
  delay_days: number;
  days_since_disclosure: number;
  amount_min: number | null;
  amount_max: number | null;
  amount_mid_estimated: number | null;
  strike: number | null;
  expiration: string | null;
  contracts: number | null;
  price_at_transaction: number | null;
  price_at_disclosure: number | null;
  price_now: number | null;
  change_since_transaction: number | null;
  change_since_disclosure: number | null;
  est_shares: number | null;
  source: string;
  source_url: string | null;
  filing_id: string | null;
  owner: string;
  owner_name: string;
  notes: string | null;
  confidence_level: string;
  analysis_status: string;
  price_data_type: string;
  instrument: Instrument;
  decay: Decay;
  score: Score;
  position_status?: "open" | "closed";
}

export interface AIAnalysis {
  engine: string;
  sections: Record<string, string[]>;
  titles: Record<string, string>;
  disclaimer: string;
}

export interface Meta {
  app: string;
  disclaimer: string;
  today: string;
  providers: Record<string, string>;
  mock_mode: boolean;
}

export interface SignalComponent {
  key: string;
  label: string;
  score: number;
  weight: number;
  detail: string;
}

export interface TickerSignals {
  ticker: string;
  name: string;
  price: number;
  sector: string | null;
  components: SignalComponent[];
  overall: number;
  classification: string;
  tone: Tone;
}
