# Addendum A — Asia continuous state across H1/H2 boundary

**Frozen:** 2026-08-26, before any Asia reaction result is generated or inspected.

The Asia session (`18:00–03:00 America/New_York`) can cross the UTC H1/H2 boundary. Therefore the reaction runner must:

1. build C5 E-BUY sticky/display episode state continuously across the full Aug-2024 → Jul-2026 chronology;
2. never reset episode identity, arming, or consumption merely because the UTC H1/H2 split is crossed;
3. preserve the normal session break at 03:00→18:00 NY, which naturally breaks one-step C5 continuity;
4. assign reaction evidence to H1 or H2 by **contact timestamp** using the frozen UTC windows;
5. keep one fresh contact maximum per display episode per Asia session;
6. evaluate every contacted episode only until that Asia session's 03:00 NY end, even if the UTC H1/H2 boundary is crossed during the same Asia session.

This is a bookkeeping/causality clarification only. It does not change zone geometry, cadence, family architecture, trigger, target, invalidation, or session hours.
