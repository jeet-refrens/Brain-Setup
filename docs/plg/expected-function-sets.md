# Expected function sets per nature of business

What "fully covered" means for each kind of business. This is the denominator for
breadth. Without it, a knowledge services firm with no stock looks under-adopted when it
is simply not a stock business.

Status: **draft priors, for the session with sales.** Nothing here is evidence yet.
Last updated 20 August 2026.

## The rule

**Nature of business gives a prior, not a rule.**

Sales already works this way. Nature sets the pre-sales mindset. The real pitch comes
from the conversation. PLG does the same thing, where behaviour is the conversation.

1. **Start from the prior.** Nature sets which functions we expect.
2. **Update from behaviour.** A knowledge services business that raises a purchase order
   has told us it buys. Buy becomes expected for it, whatever the prior said.
3. **A prior can only add an expectation. Only behaviour can remove one.** This stops us
   writing off a segment because a stereotype said the module did not apply.

**Businesses with no nature get the General set.** Nature was introduced recently and is
blank for about 57% of businesses. The General set is also the global stage ladder, so
there is one mechanism to maintain, not two.

## Read this before using the numbers below

**Current usage is not the expected set.** Buy sits at 0 to 8% everywhere. Set
expectations from today's behaviour and you would conclude nobody needs it. That is the
gap we are trying to close, not evidence that it does not matter.

Usage tells us the **gap**. Domain judgement sets the **expectation**. Keep them apart.

**Classified and unclassified businesses differ, and we do not know why.** Businesses
with no nature show Sell at 96% and Books at 9%. Classified ones show Sell around 77%
and Books between 33% and 67%. The difference runs in opposite directions depending on
the function, so this is not simply "sales works the engaged ones". Do not read the
per-nature rows as population rates until someone explains what triggers classification.

## Current coverage, from real records

**Not from feature flags.** `featureUsage` is unreliable right now. Every figure below is
counted from actual records:

| Function | Counted from |
|---|---|
| Sell | `businesses.accounting.*` counters for INVOICE, QUOTATION, PROFORMAINV, SALESORDER, DELIVERYCHALLAN |
| Buy | `accounting.EXPENDITURE.TOTAL` + `accounting.PURCHASEORDER.TOTAL` |
| Money | an invoice with `status` of `PAID` or `PARTIAL` |
| Stock | `inventorytransactions` with `transactionType` of `UPDATE` or `BLOCK` |
| CRM | a row in `leads` |
| Books | `businessConfigurations.syncAccounting.accountingSetup.status` of DONE, SCHEDULED or REQUESTED |
| Team | `businesses.users` longer than 1 |
| PayAcct | a row in `paymentaccounts` |

Stratified sample, 210 businesses per nature, created 1 June to 20 August 2026.
Percentages carry about +/- 7 points at this sample size.

| Nature | n | Sell | Buy | Money | Stock | CRM | Books | Team | PayAcct |
|---|---|---|---|---|---|---|---|---|---|
| (no nature) | 210 | 96 | 8 | 22 | 2 | 33 | 9 | 2 | 54 |
| Knowledge Services | 210 | 81 | 1 | 14 | 1 | 20 | 46 | 0 | 37 |
| Trading/Distribution | 210 | 88 | 4 | 4 | 15 | 30 | 67 | 1 | 15 |
| Retail | 210 | 77 | 0 | 2 | 0 | 12 | 60 | 0 | 14 |
| Manufacturing | 210 | 79 | 3 | 4 | 41 | 24 | 42 | 1 | 15 |
| Contracting Services | 210 | 77 | 3 | 3 | 11 | 30 | 50 | 1 | 19 |
| Digital Store | 210 | 66 | 2 | 7 | 1 | 9 | 38 | 1 | 19 |
| S/w Product | 210 | 70 | 2 | 15 | 0 | 25 | 33 | 1 | 31 |
| **All** | **1,890** | **78** | **3** | **9** | **8** | **22** | **43** | **1** | **26** |

Sell is the only function that is well covered anywhere.

### What changed when we stopped using flags

| Function | Flag said | Real records say | Why |
|---|---|---|---|
| **Money** | 11 to 28% | **2 to 22%** | flags counted a payment account existing, not a payment recorded |
| **Stock** | 1 to 75% | **0 to 41%** | flags counted inventory being switched on. Counting only real `UPDATE` or `BLOCK` movements, Manufacturing drops from 75% to 41% |
| **Books** | 8 to 48% | **9 to 67%** | accounting sync is more common than the flag showed |

**One number to treat with care.** Books is counted from an accounting setup status. Some
of that may be set by the system rather than chosen by the user. Confirm before treating
Books coverage as a user decision.

**Counting `inventorytransactions` rows without filtering gives 79% on Stock.** Every
document line writes a row, including `IGNORE` rows for items that are not stock managed.
Always filter to `UPDATE` or `BLOCK`.

## Draft priors

`core` = expected for nearly every business of this kind.
`likely` = expected for many, confirm from behaviour.
`no` = do not expect it, and do not count it as a gap.

| Nature | Sell | Buy | Money | Stock | CRM | Books | Team |
|---|---|---|---|---|---|---|---|
| **General** (no nature) | core | core | core | likely | likely | core | likely |
| **Knowledge Services** | core | core | core | **no** | likely | core | likely |
| **Trading/Distribution** | core | core | core | core | likely | core | likely |
| **Retail** | core | core | core | core | likely | core | likely |
| **Manufacturing** | core | core | core | core | likely | core | likely |
| **Contracting Services** | core | core | core | likely | core | core | likely |
| **S/w Product** | core | likely | core | **no** | core | core | likely |
| **Digital Store** | core | core | core | likely | likely | core | likely |

Two notes for the session:

- **S/w Product should probably have recurring invoices as core**, not just Sell.
  Subscription billing is the whole shape of that business.
- **Contracting Services bids for work**, so quotations and CRM sit higher than for a
  retailer who sells across a counter.

## The gaps this produces

Take `core` minus real coverage:

| Nature | Biggest gap | Second | Third |
|---|---|---|---|
| Knowledge Services | Buy, 99 | Money, 86 | Books, 54 |
| Trading/Distribution | Buy, 96 | Money, 96 | Stock, 85 |
| Retail | Buy, 100 | Stock, 100 | Money, 98 |
| Manufacturing | Buy, 97 | Money, 96 | Stock, 59 |
| Contracting Services | Buy, 97 | Money, 97 | CRM, 70 |
| Digital Store | Buy, 98 | Money, 93 | Books, 62 |
| S/w Product | Money, 85 | CRM, 75 | Books, 67 |
| General (no nature) | Buy, 92 | Books, 91 | Money, 78 |

**Buy and Money are the top two gaps in almost every nature.** Neither is module
specific. A feature-by-feature view hides this, because each gap looks small and local
on its own.

### The clearest single gap in the product

**26% of businesses create a payment account. Only 9% ever mark an invoice paid.**

They do the setup step and never do the thing the setup was for. That is 17 points of
businesses who already showed intent, sitting one behaviour away from covering the Money
function. High reach, narrow ask, and no new feature needed.

**Retail is the worst served nature on every count.** Stock 0%, Buy 0%, Money 2%, and
zero paid businesses in a sample of 210. Manufacturing manages 41% on Stock, so the
product clearly supports it. Either retailers on Refrens do not track stock, or they are
misclassified, or the product does not fit how a retailer works. Those three have very
different consequences and we should not guess.

## How to run the session

Give sales the draft table and ask one question per nature:

> Which functions would you **expect** a business of this kind to need, if it ran its
> whole operation on Refrens?

Not "which do they use", and not "which do we sell them". We are after the target, not
today's behaviour and not today's pitch.

Then capture three things per nature:

1. Corrections to `core` / `likely` / `no`
2. Anything the eight functions do not cover for that nature
3. Which gap they would attack first, and why

Their answer to 3 is a hypothesis, not a decision. It goes into the ranking in
[README.md](README.md) alongside reach, gap and effort.

## What happens after the session

1. Lock the expected sets.
2. Compute per business: expected functions active, divided by expected functions.
3. That number is the **coverage score**. It is the S3 to S4 measure.
4. Rank transitions by `reach x gap x impact`. Pick the top one. Design the experiment.
