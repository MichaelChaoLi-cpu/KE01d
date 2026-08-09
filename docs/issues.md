# Research Output Issues

## Issues

| # | item | type | severity | description |
|---|---|---|---|---|
| 1 | Table_scenario_performance_and_robustness.xlsx; Table_full_factorial_scenario_performance_and_robustness_appendix.xlsx | table / analysis | minor | A few high-load-point-failure combinations show a negligible increase rather than a loss in protected share because the deterministic whole-mesh feasibility screen reorders assignments separately by point state. The main table clips these negative losses to zero. This discrete packing artifact does not alter the reported scenario pattern, but the appendix or manuscript interpretation should disclose it rather than imply that every zero represents exact equality. |
| 2 | src/analyses/_figure_style.py | script | minor | The shared style dictionary retains two unused labels for “Worst single-point failure” and “Worst single announced-point failure.” No current output uses these labels, but removing them would prevent the deprecated worst-case terminology from being reintroduced during later regeneration. |

## Severity Summary

| severity | count |
|---|---:|
| critical | 0 |
| major | 0 |
| minor | 2 |

## Recommended Next Steps

- 两项均不影响主要研究结论，也不阻止进入 build-content-dictionary。
- 在论文解释鲁棒性表时，注明逐网格离散装载与排序可能产生极小的非单调变化；不要把所有零损失解释为严格相等。
- 后续整理共享绘图样式时删除两个未使用的旧 worst-case 标签。
- 人类确认重新计算的 Marginal Protection Gains from Additional Tankers 后，将其 Section 8 状态改回 done，然后可以继续 build-content-dictionary。
