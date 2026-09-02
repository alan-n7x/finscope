export interface AccountProps {
  name: string;
  type: string;
  balance: number;
  balance_source?: string;
}

export class Account {
  private props: AccountProps;

  constructor(props: AccountProps) {
    this.props = props;
  }

  get name(): string { return this.props.name; }
  get type(): string { return this.props.type; }
  get balance(): number { return this.props.balance; }
  get balance_source(): string { return this.props.balance_source || 'ledger'; }

  toJSON(): AccountProps {
    return { ...this.props };
  }
}
