# PLG foundation

The thing to read before starting any product-led growth work at Refrens. It says what
we are trying to move, how we decide what to work on, and how we know if it worked.

Last updated 20 August 2026. Everything marked **fact** was measured against production.
Everything marked **assumption** has not been proved yet.

## The goal

Get more businesses to run their real operations on Refrens. Money follows that. Before
payment it shows up as conversion. After payment it shows up as renewal.

## The spine: state, not cohort, not feature

Every piece of PLG work answers one shape of question:

> A business in **state X**, filtered to **segment Y**, gets **lever Z** to reach
> **state X+1**.

- **State** is what a business has and has not done yet. This is the spine.
- **Segment** is who they are: trial or paid, India or not, nature of business.
- **Lever** is what we do: a feature, a nudge, an onboarding change, a price gate.

Cohort and feature are still in the model. Neither is the spine.

**Why not cohort.** Trial and paid is not a behavioural line. 79% of converters pay
*after* their trial has expired, and 54% pay more than 30 days after signup (**fact**).
Two businesses in the same signup cohort convert at 0.06% and 14.3% depending on what
they did (**fact**). Cohort tells you almost nothing about what to do next.

**Why not feature.** Feature-first means every module owner pushes their own feature and
one business gets a dozen unrelated nudges. It is also wrong on the evidence: the
features with the best-looking conversion numbers are markers of businesses that already
committed, not causes of commitment.

**The rule this buys us:** a feature does not get a campaign because it shipped. It gets
one because it moves a named transition for a named state.

## The states

| | State | Definition | Where businesses sit |
|---|---|---|---|
| S0 | **Registered** | signed up, no document | ~20% |
| S1 | **Tried** | 1 to 2 documents | ~70% of never-payers |
| S2 | **Repeating** | 3 or more documents in 14 days | the activation event |
| S3 | **Broadened** | 2 or more business functions in use | rare early |
| S4 | **Dependent** | the functions expected for its nature are covered | - |

Payment is **not** a rung. It is an outcome measured against the ladder. That is what
lets one model serve the whole journey. Before payment the outcome is conversion. After
payment it is renewal.

A paid business that slides from S4 back to S2 has the same problem as a trial business
at S2. Same diagnosis, different channel. Organised by cohort, those look like two
unrelated problems on two different teams.

## The two metrics

**Activation = S1 to S2. Repetition.**

Measured 20 Aug 2026 on 63,605 businesses created Jan to Mar 2026. Behaviour counted
only in the first 14 days. Converters are restricted to those who paid **after** day 14.
So nothing measured here can be a result of paying (**fact**):

| Behaviour in first 14 days | Converters (n=706) | Never paid (n=2,000) | Lift |
|---|---|---|---|
| Made any document | 81.9% | 79.1% | **1.0x** |
| Created an invoice | 59.6% | 57.5% | **1.0x** |
| Created a quotation | 33.3% | 22.9% | 1.5x |
| **3 or more documents** | **46.0%** | **9.2%** | **5.0x** |
| 11 or more documents | 7.1% | 0.7% | 10.1x |
| 2 or more functions | 0.8% | 0.2% | tiny numbers |

Reweighted to the whole cohort: **3+ documents in the first 14 days converts at 5.32%.
0 to 2 documents converts at 0.67%. An 8x difference.**

Two things follow, and both are counter-intuitive:

- **Creating an invoice is not activation.** It reads 1.0x. So does "made any document".
  These are the metrics most teams would pick, and both are worthless here.
- **Breadth is not an early signal.** Under 1% of future payers used two functions in
  their first 14 days. Breadth is a later stage, not an activation event.

**Adoption = S2 to S3. Breadth.**

Counted as business functions in use, from [function-map.md](function-map.md).

**Assumption, not yet proved:** depth drives conversion, breadth drives retention. The
test is whether breadth in the 90 days before a renewal date predicts renewing. Run it
before betting anything large on breadth.

## What we know is broken

All figures from real records, not feature flags.

| Gap | Size | Note |
|---|---|---|
| **S1 stuck** | ~70% of never-payers sit at 1 to 2 documents | biggest single prize in the product |
| **Money uncovered** | only **9%** ever mark an invoice paid | 26% create a payment account first. They do the setup and never do the thing |
| **Buy uncovered** | **3%** overall, 0 to 8% in every nature | applies to everyone, used by almost nobody |
| **Stock uncovered** | **8%** overall | Manufacturing reaches 41%, Retail 0% |
| **Team uncovered** | **1%** | least covered function in the product |

## How to pick what to work on

Rank **transitions**, not features. Features then compete to serve the top transition.

| Criterion | Where it comes from |
|---|---|
| Reach | how many businesses sit in that state |
| Gap | what share never make the transition |
| Impact | the conversion or renewal difference between the two states |
| Confidence | is that difference causal, from past experiments |
| Nudgability | measured lift from past tests on this transition |
| Effort | build estimate |

`Reach x Gap x Impact` sizes the prize. Confidence and Nudgability discount it. Effort
divides it.

**Never rank by conversion rate.** Rare functions all look spectacular: credit note 53%,
API 56%, bulk upload 36%. Every one of those came from lifetime counters read after
conversion. Measured properly, before payment, credit note is a 2.1x lift on three
businesses. Conversion rate is for **validating** a choice, not making it.

## How to run an experiment

**Primary metric is the state transition, not conversion.** Conversion runs at a 1.6%
base rate with a 65-day median lag. To see a 20% lift on it you need about **24,600
businesses per arm** and a quarter of waiting. The same 20% lift on the S1 to S2
transition needs about **4,000 per arm** and reads in 14 to 30 days.

So:

- **Primary:** the transition rate. Treatment against holdout. Read at 14 or 30 days.
- **Secondary:** conversion and renewal. Read later. Underpowered on purpose. Use for
  direction, never for the go or no-go decision.
- **Guardrail:** unsubscribes, complaints, support tickets.
- **Holdout:** 80/20 works. There is a working example in
  `analysis/ocr-adoption-campaign/`.
- **Write the decision rule down before starting.** What result ships it, what result
  kills it, when we read it.

**Do not optimise opens or clicks.** They are for diagnosing why a behaviour did not
happen, never for judging whether the work succeeded.

## The chain from feature to money

```
feature used  ->  function covered  ->  S2/S3/S4 reached  ->  conversion / renewal
```

Each arrow is a separate claim that needs its own evidence. A feature that cannot name
the function it covers, and the transition that function serves, is not ready for a
lifecycle campaign. It gets a release note.

## The lifecycle rule

The next nudge depends on the business's current state, never on a campaign calendar.

**Next best action** = the highest value **expected but inactive** function, picked by
how close it is to what the business already does. Expected comes from
[expected-function-sets.md](expected-function-sets.md).

Worked example: a business creating quotations has deals in progress. That makes CRM the
adjacent function. A business creating invoices with no payments recorded has Money
adjacent.

## What we can measure

| Question | Field |
|---|---|
| Ever converted | `businesses.premium.paymentActivated: true` |
| Paying today | `businesses.premium.enabled: true` and `premium.onTrial != true` |
| When it converted | `subscriptions.recurrences[]`, the `PAYMENT*` element's `createdAt` |
| Amount paid, renewals | the paid invoice, via `recurrences[].invoice` |
| Why they trialled | `subscriptions.recurrences[]`, the `TRIAL` element's `reason` |
| Which features are used | `businessacquisitions.featureUsage.<feature>` |
| Documents by type | `businesses.accounting.<TYPE>.TOTAL` (**lifetime, see trap**) |

Read [../data/verified/refrens-mongo.md](../data/verified/refrens-mongo.md) before
writing any query. Four fields look like a conversion date and none of them is one.

**The trap that will catch you:** `accounting.*` counters are lifetime totals read today.
For a business that converted they include everything it did **after** paying. Never use
them to claim a behaviour caused a conversion. Window the behaviour before the conversion
date instead.

## What we cannot measure

- **Campaign delivery is not in Metabase.** WebEngage sends live in exported CSVs. Every
  "who got messaged" join is manual today.
- **There is no in-product event stream.** We see state, not attempts. We cannot tell
  "tried and failed" from "never tried".
- **`featureUsage.firstUsedAt` starts 12 June 2026.** Use `usedInLifetime` as a boolean
  before that date.

## Open assumptions

1. Breadth drives retention. Untested. The renewal test settles it.
2. The S1 to S2 transition is nudgable. Unknown until we try to move it.
3. Expected function sets per nature are drafts, not evidence.

## The other documents

- [function-map.md](function-map.md) - every function, which side of the business it
  serves, and whether we can measure it
- [expected-function-sets.md](expected-function-sets.md) - what "covered" means per
  nature of business
