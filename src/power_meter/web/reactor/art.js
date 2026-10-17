"use strict";

// Schematic drawings for each building, in the style of an old plant diagram.
// Static markup only: no user data goes into these strings.

window.ReactorArt = {
  dynamo: `
    <svg viewBox="0 0 120 90" aria-hidden="true">
      <rect x="18" y="70" width="84" height="8" class="rx-steel"/>
      <rect x="30" y="30" width="54" height="40" rx="6" class="rx-enamel"/>
      <path d="M38 30v40M46 30v40M54 30v40M62 30v40M70 30v40" class="rx-line-thin"/>
      <circle cx="92" cy="50" r="15" class="rx-housing"/>
      <g class="rx-spin" style="transform-origin:92px 50px">
        <path d="M92 50l0-12M92 50l12 0M92 50l0 12M92 50l-12 0" class="rx-blade"/>
      </g>
      <circle cx="92" cy="50" r="3" class="rx-ink-fill"/>
      <circle cx="24" cy="38" r="4" class="rx-lamp"/>
    </svg>`,
  solar: `
    <svg viewBox="0 0 120 90" aria-hidden="true">
      <path d="M40 78l6-22M80 78l6-22" class="rx-line"/>
      <rect x="14" y="78" width="92" height="5" class="rx-steel"/>
      <g class="rx-panel">
        <path d="M20 58L36 22h68L88 58z" class="rx-cell-blue"/>
        <path d="M28 40h68M24 49h68M44 22l-12 36M64 22l-12 36M84 22l-12 36" class="rx-line-thin-light"/>
        <path d="M20 58L36 22h68L88 58z" class="rx-outline"/>
      </g>
      <path d="M44 22h8L40 58h-8z" class="rx-glint"/>
    </svg>`,
  wind: `
    <svg viewBox="0 0 120 90" aria-hidden="true">
      <path d="M57 30L52 84h16L63 30z" class="rx-enamel"/>
      <rect x="40" y="82" width="40" height="5" class="rx-steel"/>
      <g class="rx-spin-slow" style="transform-origin:60px 28px">
        <path d="M60 28C56 18 57 6 60 2c3 4 4 16 0 26z" class="rx-blade-fill"/>
        <path d="M60 28C56 18 57 6 60 2c3 4 4 16 0 26z" class="rx-blade-fill" transform="rotate(120 60 28)"/>
        <path d="M60 28C56 18 57 6 60 2c3 4 4 16 0 26z" class="rx-blade-fill" transform="rotate(240 60 28)"/>
      </g>
      <circle cx="60" cy="28" r="4" class="rx-ink-fill"/>
    </svg>`,
  lab: `
    <svg viewBox="0 0 120 90" aria-hidden="true">
      <rect x="14" y="78" width="92" height="5" class="rx-steel"/>
      <path d="M50 12h20M54 12v22L34 74a4 4 0 0 0 4 4h44a4 4 0 0 0 4-4L66 34V12" class="rx-glass"/>
      <path d="M41 60h38l7 14a4 4 0 0 1-4 4H38a4 4 0 0 1-4-4z" class="rx-liquid"/>
      <circle cx="52" cy="70" r="3" class="rx-bubble"/>
      <circle cx="62" cy="72" r="2" class="rx-bubble rx-bubble-2"/>
      <circle cx="70" cy="68" r="2.5" class="rx-bubble rx-bubble-3"/>
      <path d="M54 12v22L34 74a4 4 0 0 0 4 4h44a4 4 0 0 0 4-4L66 34V12" class="rx-outline"/>
    </svg>`,
  battery: `
    <svg viewBox="0 0 120 90" aria-hidden="true">
      <rect x="14" y="78" width="92" height="5" class="rx-steel"/>
      <rect x="24" y="22" width="72" height="54" rx="4" class="rx-housing"/>
      <rect x="36" y="16" width="10" height="6" class="rx-ink-fill"/>
      <rect x="74" y="16" width="10" height="6" class="rx-ink-fill"/>
      <rect x="32" y="30" width="12" height="38" class="rx-charge"/>
      <rect x="48" y="30" width="12" height="38" class="rx-charge rx-charge-2"/>
      <rect x="64" y="30" width="12" height="38" class="rx-charge rx-charge-3"/>
      <rect x="80" y="30" width="8" height="38" class="rx-charge rx-charge-4"/>
    </svg>`,
  fission: `
    <svg viewBox="0 0 120 90" aria-hidden="true">
      <path d="M16 46a44 34 0 0 1 88 0" class="rx-dome"/>
      <rect x="16" y="46" width="88" height="36" class="rx-concrete"/>
      <rect x="26" y="52" width="68" height="26" class="rx-water"/>
      <rect x="26" y="52" width="68" height="26" class="rx-cherenkov"/>
      <path d="M38 56v20M46 56v20M54 56v20M62 56v20M70 56v20M78 56v20" class="rx-rod"/>
      <rect x="16" y="46" width="88" height="36" class="rx-outline"/>
      <path d="M16 46a44 34 0 0 1 88 0" class="rx-outline"/>
    </svg>`,
  fusion: `
    <svg viewBox="0 0 120 90" aria-hidden="true">
      <rect x="14" y="80" width="92" height="5" class="rx-steel"/>
      <ellipse cx="60" cy="48" rx="46" ry="26" class="rx-housing"/>
      <ellipse cx="60" cy="48" rx="22" ry="11" class="rx-hole"/>
      <ellipse cx="60" cy="48" rx="34" ry="18" class="rx-plasma"/>
      <path d="M22 34v28M40 25v46M80 25v46M98 34v28" class="rx-coil"/>
    </svg>`,
};
