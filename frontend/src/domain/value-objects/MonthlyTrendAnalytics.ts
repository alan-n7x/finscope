export interface MonthlyTrendItemProps {
  month: string;
  income: number;
  expense: number;
  net: number;
}

export class MonthlyTrendAnalytics {
  private items: MonthlyTrendItemProps[];

  constructor(items: MonthlyTrendItemProps[]) {
    this.items = items;
  }

  getItems(): MonthlyTrendItemProps[] {
    return this.items;
  }
}
