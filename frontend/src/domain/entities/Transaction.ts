export type TransactionType = 'Receita' | 'Despesa' | 'Transferência';
export type PaymentStatus = 'Sim' | 'Não';

export interface TransactionProps {
  id: number;
  date: string;
  month: string;
  type: TransactionType;
  category: string;
  description: string;
  payment_method: string;
  amount: number;
  essential: string;
  paid: PaymentStatus;
  obs?: string;
  account: string;
}

export class Transaction {
  private props: TransactionProps;

  constructor(props: TransactionProps) {
    this.props = props;
  }

  get id(): number { return this.props.id; }
  get date(): string { return this.props.date; }
  get month(): string { return this.props.month; }
  get type(): TransactionType { return this.props.type; }
  get category(): string { return this.props.category; }
  get description(): string { return this.props.description; }
  get payment_method(): string { return this.props.payment_method; }
  get amount(): number { return this.props.amount; }
  get essential(): string { return this.props.essential; }
  get paid(): PaymentStatus { return this.props.paid; }
  get obs(): string | undefined { return this.props.obs; }
  get account(): string { return this.props.account; }

  isPaid(): boolean {
    return this.props.paid.toLowerCase() === 'sim';
  }

  isIncome(): boolean {
    return this.props.type === 'Receita';
  }

  isExpense(): boolean {
    return this.props.type === 'Despesa';
  }

  toJSON(): TransactionProps {
    return { ...this.props };
  }
}
