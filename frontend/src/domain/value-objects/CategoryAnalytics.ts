export interface CategoryItemProps {
  name: string;
  value: number;
  percentage: number;
  color: string;
}

export class CategoryAnalytics {
  private items: CategoryItemProps[];

  constructor(items: CategoryItemProps[]) {
    this.items = items;
  }

  getItems(): CategoryItemProps[] {
    return this.items;
  }

  getTotalExpense(): number {
    return this.items.reduce((acc, item) => acc + item.value, 0);
  }
}
