# Changelog

All notable changes to this project are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and this project adheres
to [Semantic Versioning](https://semver.org/).

## [1.0.0] - 2026-06-27

### Added
- Stripe-subscription-driven access control for Telegram/Discord communities.
- Membership lifecycle service decoupled from Stripe and chat providers.
- Idempotent Stripe webhooks and a periodic expiry sweep worker.
- In-memory / fake adapters for local use and tests.
