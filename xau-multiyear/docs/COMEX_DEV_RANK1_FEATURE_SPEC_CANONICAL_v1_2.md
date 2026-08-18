# XAUUSD Reaction Zones — COMEX DEV_RANK1 Feature Specification CANONICAL v1.2

Date: 2026-08-18
Status: pre-acquisition amendment, superseding conflicting parts of v1/v1.1.

## Purpose

Avoid an unbudgeted and unnecessary second full-tape session for every selected DEV_RANK1 date while preserving the COMEX-native-zone study.

## Prior-session exact profile

An exact completed immediately-prior GC session profile is **not a required primary B2 feature in DEV_RANK1** unless its trade tape is already available without an additional purchase.

Therefore DEV_RANK1 does not automatically buy the prior auction session for every selected research date merely to compute prior POC/VAH/VAL/VWAP.

Primary existing-POI B2 features use:

- local trade-flow windows ending at the causal decision cutoff;
- current canonical GC auction-session-to-date VWAP/CVD/profile state ending at the cutoff;
- continuous M1 context.

If an immediately-prior exact profile happens to be available from an already-acquired session, it is descriptive/secondary unless a later protocol amendment freezes a uniformly available prior-profile design before replication.

## COMEX-native zones

The COMEX-native-zone study remains fully active.

For every selected full GC session whose tape is acquired:

1. construct its terminal VWAP, POC, VAH, VAL and preregistered secondary HVN/LVN/void levels after the session is complete;
2. timestamp when each level becomes known;
3. search subsequent continuous M1 data for prospective candidate retest times without using future outcomes to select levels;
4. store retest timestamps and XAU synchronization metadata;
5. if exact GC tape at a future retest is not already acquired, defer that retest tape to a separately quoted/authorized Stage 2.

Thus a selected session is a **source session** for future native-zone tests; it does not require the previous session to be purchased.

## No retrospective privilege

A prior-profile feature may not be introduced into DEV_RANK2 or later confirmation simply because the subset where it was available looked favorable in DEV_RANK1.

## Other rules

All causal cutoffs, side=N uncertainty handling, session boundaries, roll resets, profile algorithms, family balancing and preregistered statistical rules remain unchanged except where a later canonical amendment explicitly supersedes them.
