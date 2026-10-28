# 1. Record architecture decisions

Date: 2026-10-28

## Status

Accepted

## Context

This project makes decisions about data handling, agent permissions, verification and evaluation
that later contributors and reviewers need to understand. The reasoning behind these decisions is
easily lost if it lives only in commit messages or conversations.

## Decision

We record significant architecture decisions as Architecture Decision Records (ADRs), following
the format described by Michael Nygard in
[Documenting Architecture Decisions](https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions).

- ADRs live in `docs/adr/` and are named `NNNN-short-title.md`, numbered in sequence.
- Each ADR has the sections Status, Context, Decision and Consequences.
- An accepted ADR is not edited to change its decision. It is superseded by a new ADR that
  links back to it.

## Consequences

- The reasons behind a decision can be reviewed alongside the code it affects.
- Writing an ADR adds a small cost to each significant decision.
- Reviewers can check that a change is consistent with the decisions already recorded.
