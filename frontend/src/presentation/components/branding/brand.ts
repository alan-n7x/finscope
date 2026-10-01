import type { ComponentType } from 'react';
import { Wallet } from 'lucide-react';

export interface LogoMarkProps {
  size?: number | string;
  className?: string;
}

export interface BrandConfig {
  /** Display name shown next to the mark (expanded sidebar, login, etc.). */
  name: string;
  /** Route the logo links to (homepage). */
  homePath: string;
  /**
   * The logo mark component. Any lucide icon or custom SVG component
   * accepting `size`/`className` works here.
   */
  LogoMark: ComponentType<LogoMarkProps>;
  /** Mark background (gradient or solid). */
  markGradient: string;
}

/**
 * Single source of truth for branding.
 *
 * To swap the logo (rebrand, seasonal doodle like Google, etc.),
 * edit ONLY this file: change `LogoMark` and/or `markGradient`.
 * Every consumer (`BrandLogo`, login, splash, ...) picks it up automatically.
 */
export const brand: BrandConfig = {
  name: 'Finscope',
  homePath: '/',
  LogoMark: Wallet,
  markGradient: 'linear-gradient(135deg, var(--primary), var(--accent-blue))',
};
