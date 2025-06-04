**Error Cell(s):** Debt, H28

**Error Type:** Formula inclusion error

**Error Explanation:** The average debt balance calculation for the revolving credit facility incorrectly includes cell F18 in the range F18:H18. Cell F18 appears to be empty or zero based on the formatting, but including it in a 3-cell average when calculating the average balance between two periods (prior year-end G18 and current year-end H18) is mathematically incorrect for debt interest calculations.

**Error Fix:** Change formula from "=AVERAGE(F18:H18)" to "=AVERAGE(G18:H18)" to properly calculate the average balance between beginning and ending periods.

**Error Cell(s):** Debt, H32

**Error Type:** Formula inclusion error  

**Error Explanation:** Similar to the revolving credit facility, the long-term debt average balance calculation incorrectly includes cell F24 in the range F24:H24. This creates a 3-cell average when only the beginning balance (G24) and ending balance (H24) should be averaged for interest expense calculations.

**Error Fix:** Change formula from "=AVERAGE(F24:H24)" to "=AVERAGE(G24:H24)" to properly calculate the average debt balance between periods.

**Error Cell(s):** Debt, H42

**Error Type:** Formula inclusion error

**Error Explanation:** The average cash balance calculation includes cells E41, F41, and G41 in addition to H41, creating a 4-cell average with "=AVERAGE(E41:H41)". For interest income calculations on cash, this should typically be the average between beginning and ending cash balances of the current period.

**Error Fix:** Change formula from "=AVERAGE(E41:H41)" to "=AVERAGE(G41:H41)" to calculate the proper average cash balance between beginning and ending periods for interest income calculation.

