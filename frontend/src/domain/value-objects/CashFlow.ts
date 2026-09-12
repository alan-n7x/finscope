export interface CashFlowDay {
  day: number;
  date: string;
  income: number;
  expense: number;
  cumulative_income: number;
  cumulative_expense: number;
  net: number;
}

export interface CashFlowSeries {
  month: string;
  days: CashFlowDay[];
}
