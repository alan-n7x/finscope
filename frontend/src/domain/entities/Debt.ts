export interface DebtProps {
  creditor: string;
  type: string;
  balance: number;
  installment: number;
  due_date: string;
  priority: string;
  status: string;
}

export class Debt {
  private props: DebtProps;

  constructor(props: DebtProps) {
    this.props = props;
  }

  get creditor(): string { return this.props.creditor; }
  get type(): string { return this.props.type; }
  get balance(): number { return this.props.balance; }
  get installment(): number { return this.props.installment; }
  get due_date(): string { return this.props.due_date; }
  get priority(): string { return this.props.priority; }
  get status(): string { return this.props.status; }

  toJSON(): DebtProps {
    return { ...this.props };
  }
}
