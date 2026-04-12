Apply the following additional coverage modules when the context warrants them.
Skip any module whose trigger condition is not met.

────────────────────────────────────────
DARK MODE (trigger: context explicitly mentions dark mode, theming, or color schemes)
────────────────────────────────────────
1. Verify rendering in both light and dark mode
2. Text contrast meets WCAG AA (4.5:1 minimum) in dark mode — P1
3. Theme toggle mid-flow (user switches theme during a multi-step flow)
4. Icons, illustrations, and media adapt in dark mode
5. Interactive states (hover, focus, active, disabled) are distinguishable
6. No hard-coded colors override the dark theme
7. Visual glitches without functional impact — P2; minor styling — P3

────────────────────────────────────────
ACCESSIBILITY (trigger: context describes user-facing interactive controls)
────────────────────────────────────────
1. All interactive controls are operable via screen reader (VoiceOver / TalkBack)
2. Screen reader announces label, role, and state for every toggle, button, and input
3. State changes (toggle ON/OFF, expand/collapse) are announced immediately
4. Focus order follows a logical reading sequence
5. All controls are reachable and activatable via keyboard (Tab, Space, Enter)
6. Touch targets meet minimum 44x44pt size guideline
7. Sufficient color contrast for text and icons (WCAG AA)

────────────────────────────────────────
PLATFORM-SPECIFIC (trigger: context explicitly describes a mobile app or mentions iOS/Android)
────────────────────────────────────────
1. Test on both iOS and Android where behavior may differ
2. Verify behavior after app backgrounding and foregrounding mid-flow
3. Test with system font size set to largest accessibility setting
4. Verify landscape orientation does not break layout (if supported)
5. Test interruptions: incoming call, notification, low battery alert mid-flow
6. Verify offline behavior: what happens if network drops during a save/submit

────────────────────────────────────────
PII AND PRIVACY (trigger: context explicitly involves personal data collection or storage)
────────────────────────────────────────
1. Explicit consent obtained before collecting PII — P1
2. PII masked in UI, logs, errors, URLs, and analytics — P0 if plaintext
3. PII encrypted at rest and in transit — P0
4. Only authorized roles can access PII; no IDOR — P0
5. Account deletion removes PII across all systems — P0
6. PII not sent to third parties without consent — P1
