# Financial Modeling Error Taxonomy

## Critical Errors (Red) - Errors that produce incorrect analysis outputs

### Formula Calculation Errors

#### Mathematical formula error
Incorrect operators or formula construction leading to wrong calculations. For example, using addition instead of subtraction or multiplication instead of division within formulas.

To identify this error, compare formula outputs with expected results based on inputs. Look for unusual operators in financial contexts, such as using division where multiplication would be appropriate, or addition where subtraction is required.

#### Incorrect cell references
Linking to wrong cells for calculations, which creates dependencies on unrelated or incorrect data points.

To identify this error, analyze reference patterns and verify if cell references match typical patterns for that calculation type. For example, revenue cells should reference pricing and volume inputs, while expense calculations should reference appropriate cost drivers.

#### Logical formula errors
Using logically incorrect formulas despite syntactical correctness. The formula may execute without Excel errors but produces incorrect results due to conceptual mistakes.

To identify this error, compare the formula approach with standard financial calculations for that specific metric. For instance, EBITDA should add back D&A to EBIT, or free cash flow should properly account for changes in working capital.

#### Circular references
Unintentional circular dependencies causing calculation issues where cells depend on their own output through a chain of formulas.

To identify this error, detect circular reference chains and determine if circularity is required (intentional) or accidental. Legitimate circular references should be properly managed with iteration settings.

#### Incorrect function usage
Using inappropriate Excel functions for calculations, such as using NPV instead of XNPV for uneven cash flows, or AVERAGE instead of SUM.

To identify this error, check if function usage matches typical financial modeling standards for the specific calculation. For instance, check for proper use of time-value functions or appropriate statistical functions.

### Data Integrity Errors

#### Inconsistent values
Using different values for the same item across the model, creating inconsistencies in assumptions or inputs.

To identify this error, compare instances of the same data point across different parts of the model and check for variations in hard-coded values or references that should be identical.

#### Incorrect data entry
Number typos or wrong values input, such as entering 1,234 instead of 12,340 or inverting digits.

To identify this error, compare input data with source documents and identify outliers through statistical analysis. Look for values that deviate significantly from historical trends or industry benchmarks.

#### Outdated information
Using superseded financial or market data that no longer reflects current reality.

To identify this error, check timestamps on data sources and compare with latest available information. Verify if data points match the most recent published financial statements or market information.

#### Conflicting data sources
Inconsistencies between multiple data sources used within the same model.

To identify this error, detect data points sourced from different origins and verify consistency between them. Look for contradictions in financial data pulled from different reports or systems.

### Structural Errors

#### Three-statement linkage errors
Incorrect flow of items between income statement, balance sheet, and cash flow statement.

To identify this error, verify that changes in balance sheet items properly flow to cash flow statement and check accounting equation balance. Ensure that net income flows correctly from income statement to balance sheet and cash flow statement.

#### Working capital calculation errors
Incorrect treatment of working capital items, such as improper classification or calculation of changes.

To identify this error, analyze calculation method against standard working capital definitions and verify correct categorization of current assets/liabilities. Check that working capital changes properly impact cash flow.

#### Tax calculation errors
Wrong tax rates, treatment of losses, or deferred tax items.

To identify this error, check effective tax rate against statutory rates and verify treatment of NOLs and timing differences. Ensure tax calculations reflect appropriate jurisdictional rules and accounting standards.

#### Time period misalignment
Inconsistent time periods across different sections of the model.

To identify this error, check date alignments across sheets and verify correct period matching in calculations. Ensure that historical and forecast periods align properly across all financial statements.

### Valuation Specific Errors

#### Discount rate errors
Incorrect WACC components or calculation method affecting valuation outcomes.

To identify this error, verify WACC components against market data and check calculation methodology. Ensure cost of debt, cost of equity, and capital structure weights are appropriate and consistent with the company's risk profile.

#### Terminal value errors
Wrong growth rates or incorrect perpetuity formulas leading to inaccurate long-term value estimates.

To identify this error, check terminal growth rate against long-term economic metrics and verify correct perpetuity formula usage. Ensure the terminal value calculation doesn't imply unrealistic long-term returns.

#### Enterprise/equity value bridge errors
Double-counting or omitting items in enterprise value-to-equity value bridge.

To identify this error, verify all standard components are included (debt, cash, minorities, etc.) and counted only once. Ensure the bridge between enterprise value and equity value accounts for all appropriate adjustments.

### Transaction Modeling Errors

#### Debt schedule errors
Incorrect amortization, interest calculations, or covenant testing in debt projections.

To identify this error, check formula consistency in debt waterfalls and verify correct interest rate application. Ensure debt repayments, drawdowns, and interest calculations follow the terms of the debt agreements.

#### M&A accounting errors
Incorrect treatment of goodwill, purchase price allocation, or transaction adjustments.

To identify this error, verify that purchase price equals sum of acquired assets at fair value plus goodwill. Ensure proper accounting for transaction costs and fair value adjustments to acquired assets and liabilities.

#### Sources and uses mismatches
Unbalanced or incorrect transaction funding structure.

To identify this error, confirm that sources equal uses and check for double-counting or omissions. Verify that all transaction components are properly accounted for in the financing structure.

### Control and Dependency Errors

#### Broken scenario controls
Errors in scenario or sensitivity analysis setup that prevent proper testing of different assumptions.

To identify this error, check if scenario inputs properly flow through all dependent calculations. Verify that changing scenario inputs appropriately affects all related outputs.

#### Macro/VBA execution errors
Broken automated procedures that fail to execute properly or produce incorrect results.

To identify this error, look for code references to non-existent ranges or improper variable handling. Check for error handling in code and test macro execution under different conditions.

## Non-Critical Errors (Yellow) - Suboptimal practices that don't break calculations

### Formatting and Presentation

#### Inconsistent formatting
Different number formats, alignments, or cell styles that make the model difficult to read and interpret.

To identify this error, compare formatting patterns across similar data types and identify inconsistent decimal places or number formats. Look for inconsistencies in how financial values are displayed.

#### Text and spelling errors
Typos or grammatical errors in labels and descriptions that may cause confusion.

To identify this error, apply spelling and grammar checks to text elements and verify terminology consistency. Look for industry-specific terms that might be misspelled or inconsistently used.

#### Inconsistent color coding
Irregular use of color schemes for similar elements, reducing the visual clarity of the model.

To identify this error, analyze color pattern usage across the model and check for deviations from established conventions. Verify that similar elements use consistent color coding throughout.

### Efficiency Issues

#### Excessive hard-coding
Hard-coding values that should be formula-driven, making the model less flexible and more error-prone.

To identify this error, look for isolated numbers not linked to inputs or calculations and check for hard-coded values in projection periods. Identify values that should be driven by assumptions rather than manually entered.

#### Inefficient formula construction
Using unnecessarily complex formulas that are difficult to audit and may slow model performance.

To identify this error, analyze formula complexity and identify opportunities for simplification or function substitution. Look for nested IF statements that could be simplified or complex formulas that could be broken into steps.

#### Redundant calculations
Calculating the same value multiple times instead of referencing a single calculation.

To identify this error, look for similar formulas repeated across the model instead of using references. Identify calculations that could be performed once and referenced elsewhere.

### Organization and Structure

#### Poor sheet organization
Illogical sheet order or structure that makes navigation and understanding difficult.

To identify this error, analyze sheet organization against standard modeling conventions (inputs→calculations→outputs). Check for logical flow between sheets and within calculation sequences.

#### Inconsistent naming conventions
Variable naming that lacks clear pattern, making it difficult to understand relationships between elements.

To identify this error, compare naming patterns across similar elements and identify inconsistencies in cell naming or range labels. Look for naming conventions that don't clearly indicate content or purpose.

#### Inadequate documentation
Missing or unclear model assumptions and methodology notes that make the model difficult for others to use.

To identify this error, check for presence of documentation sections and verify comprehensiveness of assumption explanations. Look for areas where calculation methodologies or assumptions are not clearly explained.

### Usability Issues

#### Missing input validation
Lack of checks for unreasonable inputs that could lead to implausible results.

To identify this error, check for absence of data validation or input range checks. Look for inputs that accept any value without warning when values outside normal ranges are entered.

#### Insufficient error handling
No error trapping or notification systems to alert users to potential problems.

To identify this error, identify formulas without error handling (e.g., IFERROR, ISERROR) where appropriate. Look for calculations that might produce errors under certain input conditions without proper handling.

#### Inadequate sensitivity controls
Limited ability to test different scenarios or sensitivity to key variables.

To identify this error, check for absence of flexible input parameters or scenario toggles. Look for areas where sensitivity analysis would be valuable but is not implemented.

### Methodology Consistency

#### Inconsistent projection methods
Using different forecasting approaches for similar items without clear justification.

To identify this error, compare methodologies across similar line items and identify inconsistent growth assumptions. Look for cases where some items are projected as percentages while similar items use absolute values.

#### Mixing accounting standards
Inconsistent application of GAAP, IFRS, or other standards within the same model.

To identify this error, check for mixing of accounting treatments that should be consistent. Look for inconsistencies in treatment of leases, revenue recognition, or other accounting-sensitive areas.

#### Inconsistent time treatments
Mixing mid-year vs. year-end conventions in valuation or cash flow timing.

To identify this error, look for inconsistent timing assumptions in DCF or other time-sensitive calculations. Verify consistent application of timing conventions for discounting and cash flow recognition.