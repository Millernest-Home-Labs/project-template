# Model Scorecard

Updated 2026-09-28 using OpenRouter's live model catalog. Prices are USD per 1M tokens.

## Current Model Pricing

| Model                                                                                         | Artificial Analysis intelligence index                       | Input         | Cache read | Output        | OpenRouter model                                                          |
| --------------------------------------------------------------------------------------------- | ------------------------------------------------------------ | ------------- | ---------- | ------------- | ------------------------------------------------------------------------- |
| [GLM 5.3 Flash](https://artificialanalysis.ai/models/glm-5-3-flash)                           | [42](https://artificialanalysis.ai/models/glm-5-3-flash)     | $0.045 (sale) | $0.01      | $0.140        | [OpenRouter](https://openrouter.ai/z-ai/glm-5.3-flash)                    |
| [DeepSeek V4 Flash 0731](https://artificialanalysis.ai/models/deepseek-v4-flash)              | [34](https://artificialanalysis.ai/models/deepseek-v4-flash) | $0.021        | $0.016     | $0.320        | [OpenRouter](https://openrouter.ai/deepseek/deepseek-v4-flash-0731)       |
| [Ling 3.0 Flash](https://artificialanalysis.ai/models/ling-3-0-flash)                         | [25](https://artificialanalysis.ai/models/ling-3-0-flash)    | $0.021        | $0.004     | $0.063        | [OpenRouter](https://openrouter.ai/inclusionai/ling-3.0-flash)            |
| [DeepSeek V4 Flash Vision Exp](https://artificialanalysis.ai/models/deepseek-v4-flash-vision) | [34](https://artificialanalysis.ai/models/deepseek-v4-flash) | $0.216 (sale) | $0.007     | $0.647 (sale) | [OpenRouter](https://openrouter.ai/deepseek/deepseek-v4-flash-vision-exp) |
| [Ling 3.0 Flash VL](https://artificialanalysis.ai/models/ling-3-0-flash-vl)                   | [25](https://artificialanalysis.ai/models/ling-3-0-flash-vl) | $0.021        | $0.004     | $0.062        | [OpenRouter](https://openrouter.ai/inclusionai/ling-3.0-flash-vl)         |
| [Claude Opus 5.5](https://artificialanalysis.ai/models/claude-opus-5-5)                       | [58](https://artificialanalysis.ai/models/claude-opus-5-5)   | $4.00         | $0.20      | $20.00        | [OpenRouter](https://openrouter.ai/anthropic/claude-opus-5.5)             |

DeepSeek V4 Flash Vision Exp is treated as having the same intelligence score as the DeepSeek V4 Flash family: 34 (the base model's score on the non-vision page). The linked Artificial Analysis page for DeepSeek V4 Flash 0731 is the canonical reference for the family intelligence score. GLM 5.3 Flash and DeepSeek V4 Flash Vision Exp are currently on sale on OpenRouter (51% off via DeepInfra) — sale pricing is reflected in the table.

OpenRouter's raw catalog values are 41.8 for GLM 5.3 Flash and 24.6 for Ling 3.0 Flash VL; the linked AA pages display those scores rounded to 42 and 25. Artificial Analysis reports $4/$20 for Opus 5.5 and a 95% cache discount, represented here as $0.20 per 1M cache-read tokens.

Cache-read pricing applies to prompt tokens served from the provider's cache. Image, video, web-search, batch, and provider-specific charges may be separate. OpenRouter's live prices supersede the older values in `README.md`. GLM 5.3 Flash and DeepSeek V4 Flash Vision Exp are currently on sale (51% off via DeepInfra for Exp).

## Recommended Assignments

| Agent         | Model                  | Reason                                                           |
| ------------- | ---------------------- | ---------------------------------------------------------------- |
| orchestrator  | GLM 5.3 Flash          | Highest agentic score in this set; multimodal coordination       |
| frontend-dev  | GLM 5.3 Flash          | Screenshot understanding plus reliable multi-file implementation |
| backend-dev   | DeepSeek V4 Flash 0731 | Strong coding at very low input/cache cost                       |
| adversary     | DeepSeek V4 Flash 0731 | Cheap code and reasoning review                                  |
| qa            | GLM 5.3 Flash          | Visual evidence plus stronger agentic judgment                   |
| visual-review | Ling 3.0 Flash VL      | Low-cost image and layout inspection                             |
| general       | Ling 3.0 Flash         | Low-cost text work                                               |
| infra         | Ling 3.0 Flash         | High-volume operational text                                     |
| platform-ops  | Ling 3.0 Flash         | Short operational tasks                                          |
| explore       | Ling 3.0 Flash         | Cheap repository exploration                                     |
| build         | Ling 3.0 Flash         | Small focused tasks                                              |
| superman      | GLM 5.3 Flash          | Strongest single-agent option in this set                        |

## Big-Gun Escalation

Claude Opus 5.5 should be an escalation model, not a default assignment. At $20 per 1M output tokens, a single long autonomous run can cost more than the normal GLM/DeepSeek/Ling workflow combined.

Use Opus 5.5 when the expected cost of another failed attempt is higher than the model premium:

- A difficult repository-level change has failed two or three times under GLM or DeepSeek.
- A production-impacting migration, security review, or incident requires the strongest available reasoning.
- The task combines unfamiliar architecture, long context, image evidence, and many dependent edits.
- A final release review needs an independent high-capability judge after the implementation is complete.
- A high-value frontend must match reference screenshots closely and the cheaper visual implementation path keeps missing important details.

Do not use Opus for routine infrastructure, ordinary QA passes, small UI edits, repository exploration, or standard backend implementation. A practical trigger is: escalate one focused task with a bounded prompt and explicit success criteria, then return the resulting findings or patch to the normal agent workflow.

## Usage Profile

The table below keeps the fields relevant to cost modeling. Output cost estimates include both output and reasoning tokens. Cache writes are zero in the supplied data, except for the orchestrator's 1,219,536 cache-write tokens, which are negligible at this scale and excluded from the estimate because no cache-write rate was supplied.

| Agent         | Sessions | Input   | Output + reasoning | Cache read | Suggested model        | Estimated cost |
| ------------- | -------- | ------- | ------------------ | ---------- | ---------------------- | -------------- |
| qa            | 289      | 122.91M | 22.28M             | 1,760.78M  | GLM 5.3 Flash (sale)   | $26.26         |
| backend-dev   | 221      | 77.10M  | 12.68M             | 1,580.91M  | DeepSeek V4 Flash 0731 | $30.97         |
| superman      | 8        | 109.14M | 5.28M              | 1,359.68M  | GLM 5.3 Flash (sale)   | $19.25         |
| frontend-dev  | 179      | 68.30M  | 7.90M              | 1,378.15M  | GLM 5.3 Flash (sale)   | $17.96         |
| orchestrator  | 10       | 111.43M | 2.12M              | 621.75M    | GLM 5.3 Flash (sale)   | $11.53         |
| adversary     | 46       | 24.23M  | 3.75M              | 616.77M    | DeepSeek V4 Flash 0731 | $11.58         |
| general       | 65       | 12.38M  | 2.19M              | 179.29M    | Ling 3.0 Flash         | $1.15          |
| infra         | 56       | 5.77M   | 1.36M              | 68.89M     | Ling 3.0 Flash         | $0.50          |
| platform-ops  | 9        | 1.67M   | 0.54M              | 16.01M     | Ling 3.0 Flash         | $0.14          |
| explore       | 8        | 1.26M   | 0.16M              | 6.89M      | Ling 3.0 Flash         | $0.07          |
| build         | 16       | 0.41M   | 0.04M              | 6.99M      | Ling 3.0 Flash         | $0.04          |
| visual-review | 19       | 1.43M   | 0.21M              | 2.12M      | Ling 3.0 Flash VL      | $0.05          |

### Estimate Method

`estimated cost = input tokens × input rate + (output + reasoning) tokens × output rate + cache-read tokens × cache-read rate`

These are counterfactual estimates using the suggested assignments and the current OpenRouter rates. They are not a reconstruction of historical provider billing, because the original agents may have used different models, routing, discounts, or cached-token treatment.

## Conclusions

- The dominant cost driver is cache reads, not ordinary input or output tokens.
- QA, superman, frontend-dev, and orchestrator account for most estimated spend because they combine high session volume or very large cached contexts with GLM pricing.
- Moving routine visual review to Ling VL is inexpensive, but its lower intelligence score makes it better suited to visual inspection than autonomous frontend implementation.
- DeepSeek V4 Flash 0731 is the economical coding choice for backend and adversarial work.
- GLM remains the strongest default for orchestration, QA judgment, and end-to-end frontend work.
