#!/usr/bin/env python3
"""Generate Full-Factorial Scenario Performance and Robustness Appendix.

Plan: Preserve the complete 162-combination robustness matrix outside the main
text. Framework: AnaSOP Sections 5-7 and the shared deterministic full-mesh
feasibility screen implemented by table_scenario_performance_and_robustness.
"""

from table_scenario_performance_and_robustness import (
    APPENDIX_OUTPUT,
    APPENDIX_PREVIEW,
    HEADERS,
    ROOT,
    construct_table,
    validate_table,
    verify_appendix_outputs,
    write_appendix_preview,
    write_appendix_workbook,
)


def main() -> None:
    table_data, audit = construct_table()
    validate_table(table_data)
    write_appendix_workbook(table_data, audit)
    write_appendix_preview(table_data)
    verify_appendix_outputs(len(table_data))
    print(
        f"Saved appendix {len(table_data)} rows x {len(HEADERS)} cols -> "
        f"{APPENDIX_OUTPUT.relative_to(ROOT)}"
    )
    print(f"Saved appendix PNG preview -> {APPENDIX_PREVIEW.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
