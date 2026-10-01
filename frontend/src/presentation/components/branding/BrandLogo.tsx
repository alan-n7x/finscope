import React from 'react';
import { NavLink } from 'react-router-dom';
import { brand } from './brand';

interface BrandLogoProps {
  /** Compact variant for the collapsed icon rail (mark only, no name). */
  compact?: boolean;
}

/**
 * App logo as a link to the homepage. Visual identity (mark, gradient,
 * name) comes from the central `brand` config — swap it there.
 */
export const BrandLogo: React.FC<BrandLogoProps> = ({ compact = false }) => {
  const LogoMark = brand.LogoMark;

  return (
    <NavLink
      to={brand.homePath}
      className={`brand-logo${compact ? ' brand-logo--compact' : ''}`}
      aria-label={`${brand.name} - página inicial`}
      title={brand.name}
    >
      <span className="brand-logo__mark" style={{ background: brand.markGradient }}>
        <LogoMark size={compact ? 16 : 20} />
      </span>
      <span className="brand-logo__name">{brand.name}</span>
    </NavLink>
  );
};
