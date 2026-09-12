export interface CashFlowDay {
  day: number;
  date: string;
  income: number;
  expense: number;
  cumulative_income: number;
  cumulative_expense: number;
  net: number;
  realized_balance: number | null;
  projected_balance: number | null;
}

export interface CashFlowSeries {
  month: string;
  days: CashFlowDay[];
  transition_date: string | null;
  start_balance: number;
  final_projected_balance: number;
  has_projection: boolean;
}
