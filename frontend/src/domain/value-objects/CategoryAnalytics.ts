export interface CategoryItemProps {
  name: string;
  value: number;
  percentage: number;
  color: string;
}

export class CategoryAnalytics {
  private items: CategoryItemProps[];
  private totalExpense?: number;

  constructor(items: CategoryItemProps[], totalExpense?: number) {
    this.items = items;
    this.totalExpense = totalExpense;
  }

  getItems(): CategoryItemProps[] {
    return this.items;
  }

  getTotalExpense(): number {
    if (this.totalExpense !== undefined) {
      return this.totalExpense;
    }
    return this.items.reduce((acc, item) => acc + item.value, 0);
  }
}
