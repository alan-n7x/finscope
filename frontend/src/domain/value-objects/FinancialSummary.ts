import { Account } from '../entities/Account';

export interface FinancialSummaryProps {
  month: string;
  ref_date?: string;
  total_balance: number;
  income_month: number;
  expense_month: number;
  net_month: number;
  projected_final: number;
  reserve_min: number;
  free_after_reserve: number;
  accounts: Account[];
}

export class FinancialSummary {
  private props: FinancialSummaryProps;

  constructor(props: FinancialSummaryProps) {
    this.props = props;
  }

  get month(): string { return this.props.month; }
  get ref_date(): string | undefined { return this.props.ref_date; }
  get total_balance(): number { return this.props.total_balance; }
  get income_month(): number { return this.props.income_month; }
  get expense_month(): number { return this.props.expense_month; }
  get net_month(): number { return this.props.net_month; }
  get projected_final(): number { return this.props.projected_final; }
  get reserve_min(): number { return this.props.reserve_min; }
  get free_after_reserve(): number { return this.props.free_after_reserve; }
  get accounts(): Account[] { return this.props.accounts; }
}
