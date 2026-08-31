export type Metrics = {
  gmv: number;
  transactions: number;
  revenue_at_risk: number;
  potential_recovery: number;
  revenue_recovered: number;
  recovery_rate: number;
  successful_interventions: number;
  human_escalations: number;
  stopped_actions: number;
  false_interventions: number;
  average_investigation_time: number;
  payment_failure_rate: number;
  currency: string;
  series: {
    revenue_at_risk: { t: string; v: number }[];
    revenue_recovered: { t: string; v: number }[];
    recovery_rate: { t: string; v: number }[];
    payment_failure_rate: { t: string; v: number }[];
  };
};

export type Incident = {
  incident_id: string;
  merchant_id: string;
  amount: number;
  root_cause?: string | null;
  risk_level: string;
  action: string;
  status: string;
  trace_id: string;
  scenario?: string | null;
  revenue_at_risk: number;
  revenue_recovered: number;
  confidence: number;
  transaction_ids: string[];
  created_at: string;
};

export type IncidentDetail = Incident & {
  explanation: string;
  moneyguard_reason: string;
  policy_reason: string;
  verified: boolean;
  agent_results: {
    agent: string;
    confidence: number;
    decision: string;
    explanation: string;
    evidence: Record<string, unknown>;
    payload: Record<string, unknown>;
    ok: boolean;
    error?: string | null;
    timestamp: string;
  }[];
};

export type AuditEvent = {
  id: number;
  timestamp: string;
  trace_id: string;
  incident_id?: string | null;
  agent: string;
  event: string;
  decision: string;
  evidence: Record<string, unknown>;
  action?: string | null;
  result?: string | null;
};

export type Evaluation = {
  detection_precision: number;
  detection_recall: number;
  root_cause_accuracy: number;
  recovery_success_rate: number;
  false_intervention_rate: number;
  human_escalation_rate: number;
  revenue_at_risk_detected: number;
  ground_truth_revenue_at_risk: number;
  revenue_recovered: number;
  transactions_evaluated: number;
  incidents_evaluated: number;
  note?: string;
};

export type DemoStep = {
  title: string;
  agent: string;
  status: string;
  confidence: number;
  evidence: Record<string, unknown>;
  explanation: string;
  decision: string;
};

export type DemoScenario = {
  id: string;
  name: string;
  description: string;
  incident_id: string;
  trace_id: string;
  root_cause: string;
  action: string;
  status: string;
  revenue_at_risk: number;
  revenue_recovered: number;
  steps: DemoStep[];
  moneyguard_reason: string;
  policy_reason: string;
};

export type DemoResponse = {
  scenarios: DemoScenario[];
  metrics: Metrics;
  evaluation: Evaluation;
  message: string;
};

// ---------------------------------------------------------------------------
// Real-time WebSocket event types
// ---------------------------------------------------------------------------

export type WSEventType =
  | "connected"
  | "ping"
  | "incident"
  | "agent_step"
  | "metrics"
  | "transaction"
  | "system";

export type WSBaseEvent = {
  type: WSEventType;
  ts: string;
};

export type WSConnectedEvent = WSBaseEvent & {
  type: "connected";
  message: string;
  subscribers: number;
};

export type WSPingEvent = WSBaseEvent & {
  type: "ping";
};

export type WSIncidentEvent = WSBaseEvent & {
  type: "incident";
  incident_id: string;
  trace_id: string;
  merchant_id: string;
  root_cause: string;
  action: string;
  status: string;
  revenue_at_risk: number;
  revenue_recovered: number;
  risk_level: string;
  confidence: number;
  scenario: string | null;
};

export type WSAgentStepEvent = WSBaseEvent & {
  type: "agent_step";
  incident_id: string;
  trace_id: string;
  agent: string;
  event: string;
  decision: string;
  confidence: number;
  ok: boolean;
};

export type WSMetricsEvent = WSBaseEvent & {
  type: "metrics";
  metrics: Metrics;
};

export type WSTransactionEvent = WSBaseEvent & {
  type: "transaction";
  transaction_id: string;
  status: string;
  amount: number;
  gateway: string;
  merchant_id: string;
  risk_score: number;
};

export type WSSystemEvent = WSBaseEvent & {
  type: "system";
  message: string;
  level: "info" | "warn" | "error";
};

export type WSEvent =
  | WSConnectedEvent
  | WSPingEvent
  | WSIncidentEvent
  | WSAgentStepEvent
  | WSMetricsEvent
  | WSTransactionEvent
  | WSSystemEvent;

/** A single entry shown in the LiveFeed panel. */
export type LiveEvent = {
  id: string;
  ts: string;
  kind: WSEventType;
  label: string;
  sub: string;
  badge?: string;
  badgeClass?: string;
};

// ---------------------------------------------------------------------------
// Transactions
// ---------------------------------------------------------------------------

export type TxRecord = {
  transaction_id: string;
  merchant_id: string;
  customer_id: string;
  amount: number;
  currency: string;
  payment_method: string;
  gateway: string;
  timestamp: string;
  status: string;
  failure_reason: string | null;
  device_id: string;
  customer_segment: string;
  retry_count: number;
  risk_score: number;
  revenue_at_risk: number;
  recovery_status: string;
  recovery_action: string;
  detected_anomaly: boolean;
  ground_truth_anomaly: boolean;
};

export type TransactionListResponse = {
  total: number;
  items: TxRecord[];
};

// ---------------------------------------------------------------------------
// Human Review
// ---------------------------------------------------------------------------

export type HumanReview = {
  incident_id: string;
  trace_id: string;
  merchant_id: string;
  amount: number;
  currency: string;
  root_cause: string | null;
  risk_level: string;
  action: string;
  status: string;
  confidence: number;
  revenue_at_risk: number;
  transaction_ids: string[];
  created_at: string;
  scenario: string | null;
  moneyguard_decision: string;
  moneyguard_reason: string;
  policy_reason: string;
  root_cause_explanation: string;
  review_reason: string;
  retry_count: number;
  ai_recommendation: string;
  review_completed: boolean;
};
