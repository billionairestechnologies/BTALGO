# BTAlgo Feature Development Guide

## Company
Billionaires Technologies

## Product
BTAlgo

---

## Purpose

Define safe rules for feature development and updates.

---

## Core Rule

**NEVER MODIFY ROOT OPENALGO PACKAGE FILES DIRECTLY**

(`blueprints/`, `broker/`, `services/`, `utils/`, `database/`, `restx_api/`)

---

## Structure

- Root packages → OpenAlgo engine (untouched)
- `btalgo/` → custom features
- `overrides/` → UI overrides
- `branding/` → assets
- `config/` → config files

---

## Feature Rules

**Allowed:**
- New files in `/btalgo/`
- Wrappers around core functions
- UI additions via overrides

**Not Allowed:**
- Editing core OpenAlgo files
- Changing APIs
- Renaming internal functions

---

## Adding a Feature

```python
# btalgo/strategies/my_strategy.py
from services.place_order_service import place_order as core_place_order

def place_order_with_custom_logic(order_data):
    # custom pre-processing
    return core_place_order(order_data)
```

---

## Update Process

```bash
git fetch upstream
git merge upstream/main
```

Then:

```bash
git checkout btalgo-features
git merge main
```

---

## Feature Toggle

Use ENV:

```
ENABLE_BTALGO_FEATURES=true
```

---

## Mistakes to Avoid

- Editing core OpenAlgo files
- Global search-replace
- Breaking imports
- Modifying `License.md`

---

## Vision

BTAlgo will evolve into:
- Multi-broker platform
- Copy trading system
- SaaS product
