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
