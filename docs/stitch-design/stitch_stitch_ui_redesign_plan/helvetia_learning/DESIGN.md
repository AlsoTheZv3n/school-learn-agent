---
name: Helvetia Learning
colors:
  surface: '#faf9fe'
  surface-dim: '#dad9de'
  surface-bright: '#faf9fe'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#f4f3f8'
  surface-container: '#eeedf2'
  surface-container-high: '#e8e7ec'
  surface-container-highest: '#e3e2e7'
  on-surface: '#1a1b1f'
  on-surface-variant: '#43474f'
  inverse-surface: '#2f3034'
  inverse-on-surface: '#f1f0f5'
  outline: '#747780'
  outline-variant: '#c4c6d0'
  surface-tint: '#405e92'
  primary: '#113566'
  on-primary: '#ffffff'
  primary-container: '#2d4c7e'
  on-primary-container: '#a0bdf7'
  inverse-primary: '#aac7ff'
  secondary: '#00696c'
  on-secondary: '#ffffff'
  secondary-container: '#9beef0'
  on-secondary-container: '#016e71'
  tertiary: '#4d2f00'
  on-tertiary: '#ffffff'
  tertiary-container: '#6c4300'
  on-tertiary-container: '#ffab31'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#d7e3ff'
  primary-fixed-dim: '#aac7ff'
  on-primary-fixed: '#001b3e'
  on-primary-fixed-variant: '#274778'
  secondary-fixed: '#9ef0f3'
  secondary-fixed-dim: '#82d4d7'
  on-secondary-fixed: '#002021'
  on-secondary-fixed-variant: '#004f52'
  tertiary-fixed: '#ffddb8'
  tertiary-fixed-dim: '#ffb95f'
  on-tertiary-fixed: '#2a1700'
  on-tertiary-fixed-variant: '#653e00'
  background: '#faf9fe'
  on-background: '#1a1b1f'
  surface-variant: '#e3e2e7'
typography:
  display-lg:
    fontFamily: Plus Jakarta Sans
    fontSize: 48px
    fontWeight: '700'
    lineHeight: '1.2'
    letterSpacing: -0.02em
  headline-lg:
    fontFamily: Plus Jakarta Sans
    fontSize: 32px
    fontWeight: '600'
    lineHeight: '1.3'
  headline-lg-mobile:
    fontFamily: Plus Jakarta Sans
    fontSize: 24px
    fontWeight: '600'
    lineHeight: '1.3'
  title-md:
    fontFamily: Plus Jakarta Sans
    fontSize: 20px
    fontWeight: '600'
    lineHeight: '1.4'
  body-lg:
    fontFamily: Plus Jakarta Sans
    fontSize: 18px
    fontWeight: '400'
    lineHeight: '1.6'
  body-md:
    fontFamily: Plus Jakarta Sans
    fontSize: 16px
    fontWeight: '400'
    lineHeight: '1.6'
  label-sm:
    fontFamily: Plus Jakarta Sans
    fontSize: 14px
    fontWeight: '500'
    lineHeight: '1.2'
    letterSpacing: 0.01em
  caption:
    fontFamily: Plus Jakarta Sans
    fontSize: 12px
    fontWeight: '400'
    lineHeight: '1.2'
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  unit: 4px
  xs: 4px
  sm: 8px
  md: 16px
  lg: 24px
  xl: 32px
  container-margin: 24px
  gutter: 16px
  teacher-density-multiplier: '0.75'
---

## Brand & Style
The design system is rooted in the principles of "Digital Sovereignty" and "Calm Technology." It balances the high-stakes responsibility of European educational data privacy with the warmth required for student engagement.

The brand personality is **Trustworthy, Kind, and Intentional**. It avoids the frenetic energy of typical "EdTech" in favor of a focused, meditative atmosphere that respects the cognitive load of both students and teachers. 

The style is **Modern Corporate with a Tactile Humanism**:
- **Student Experience:** Minimalist and spacious. High use of whitespace to reduce anxiety and promote focus.
- **Teacher Experience:** High-density and systematic. Utilizes structured data grids and information-rich dashboards while maintaining the same soft visual language to ensure brand coherence.
- **Compliance & Ethics:** Visual cues reinforce that the "Human is in the Loop." AI features are styled with a distinct but subtle visual treatment to differentiate generated content from verified pedagogical data.

## Colors
The palette is designed for prolonged screen time and high legibility.

- **Primary (Indigo):** Used for structural elements and primary actions. It evokes stability and authority.
- **Secondary (Teal):** Used for student progress and "learning" state indicators.
- **Accents (Amber/Coral):** Used sparingly for highlights, "aha" moments, and active focus states.
- **Status Tones:** Success, Warning, and Error colors are desaturated to avoid triggering "alert fatigue" while maintaining clear WCAG AA contrast ratios.

**Theming:**
- **Light Mode:** Uses a "warm paper" background (`#FDFCFB`) to reduce blue light strain.
- **Dark Mode:** High-contrast but utilizes deep navy tones (`#0F172A`) rather than pure black to prevent "halo" effects around text.

## Typography
This design system utilizes **Plus Jakarta Sans** for its friendly, geometric, yet highly professional character. Its open counters ensure readability for younger students.

- **Scale:** A major third scale is used for the student experience (larger headers), while a minor second scale is applied to the teacher dashboard to accommodate high-density data.
- **Accessibility:** An optional toggle allows users to switch the primary typeface to **Atkinson Hyperlegible Next**, specifically designed for low-vision and dyslexic readers.
- **Rhythm:** Line heights are generous (1.6x for body) to provide "breathing room" between lines of text, aiding tracking for students with ADHD or reading difficulties.

## Layout & Spacing
The layout follows a 12-column fluid grid system with distinct "Mood Densities":

- **Student Layout:** Uses a "Centered Focus" model. Max content width of 1024px. Padding is increased (spacing.xl) to isolate tasks and prevent distraction.
- **Teacher Layout:** Uses a "Full-Width Dashboard" model. Sidebars are collapsible to maximize horizontal space for data tables and heatmaps.
- **Density Scaling:** The teacher experience applies a `0.75x` multiplier to standard spacing units, allowing more information to be visible above the fold without sacrificing alignment.
- **Breakpoints:**
  - Mobile (< 640px): Single column, 16px margins.
  - Tablet (640px - 1024px): 8 columns, 24px margins.
  - Desktop (> 1024px): 12 columns, 32px margins or fixed width.

## Elevation & Depth
Depth is conveyed through **Tonal Layering** and **Ambient Shadows** to maintain a "calm" atmosphere.

- **Surfaces:** We use three levels of surface. Level 0 is the background. Level 1 is the primary card container. Level 2 is for floating elements (modals, toasts).
- **Shadows:** Avoid harsh, black shadows. Use soft, diffused Indigo-tinted shadows: `0px 4px 20px rgba(45, 76, 126, 0.08)`.
- **Teacher View:** Minimizes shadows in favor of subtle 1px borders (`neutral-gray` at 10% opacity) to keep the UI clean when displaying complex data visualizations.
- **Interactive States:** On hover, cards lift slightly (shadow intensity increases), providing a tactile feel that signals interactivity without flashy animations.

## Shapes
The shape language is consistently "Soft-Geometric." 

- **Cards & Containers:** Fixed at a `12px` (0.75rem) radius to feel approachable yet structured.
- **Buttons:** Use a slightly larger radius (rounded-lg) for a friendly, "clickable" appearance.
- **Inputs:** Match the card radius for a cohesive form language.
- **Icons:** Use rounded caps and joins to mirror the typography's soft terminals.

## Components

### Navigation & Footer
- **Top Nav:** Persistent branding on the left, profile and "Privacy Shield" status on the right.
- **Sidebar:** Icons only when collapsed; labels revealed on hover or click. Clear active-state highlight using the `secondary-teal`.
- **Footer:** Minimalist. Includes the "🇨🇭 In CH/EU gehostet" badge. The "Lehrperson behält die Kontrolle" text must be displayed in `label-sm` with a secondary-teal underline to emphasize the ethical commitment.

### Buttons & Inputs
- **Primary:** Filled `primary-indigo`. White text. High contrast.
- **Secondary:** Outlined `secondary-teal`. Transparent background.
- **Ghost:** No border. Used for tertiary actions to reduce visual noise.
- **Inputs:** White background (Light mode) or desaturated navy (Dark mode). Focus state uses a `2px` amber glow.

### Mastery Meter
- **Standard:** A smooth progress bar using a gradient from `secondary-teal` to `primary-indigo`.
- **Uncertainty Band:** For AI-assessed mastery, the bar includes a semi-transparent "shadow" area behind the main progress line, indicating the range of statistical confidence (e.g., "75% ± 5%").

### Data & Visualization
- **Heatmaps:** Uses a 5-step monochromatic scale of `secondary-teal`. Zero values remain the background color to keep the grid clean.
- **KPI Cards:** Large `display-lg` numbers with a `caption` label below. No borders; use Level 1 elevation.
- **Data Tables:** Zebra-striping in light gray. Sortable headers with clear chevron indicators.

### Feedback & Communication
- **Tutor Bubbles:** Left-aligned (Tutor) bubbles use a soft teal background. Right-aligned (Student) use a soft indigo. All bubbles use `rounded-xl`.
- **Banners:** Full-width alerts at the top of content areas. Use `info-blue`, `warning-amber`, or `error-red` with high-contrast text.