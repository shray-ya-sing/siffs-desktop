Error Cell(s): M65, N65, O65

Error Type: Incorrect cell references

Error Explanation: The repayment of current bank borrowings formulas in columns M, N, and O are referencing the wrong columns from the Debt sheet. Column M references P17, column N references Q17, and column O references R17, but they should reference M17, N17, and O17 respectively to maintain consistency with the column structure.

Error Fix: Change M65 formula from "=Debt!P17" to "=Debt!M17", N65 formula from "=Debt!Q17" to "=Debt!N17", and O65 formula from "=Debt!R17" to "=Debt!O17"