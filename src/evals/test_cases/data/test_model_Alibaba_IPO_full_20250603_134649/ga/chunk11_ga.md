**Error Cell(s):** DCF Valuations, C38

**Error Type:** Incorrect cell reference

**Error Explanation:** The equity value calculation uses an incorrect exchange rate reference. Cell C38 references C37/6.2164 but then D38 uses C38/6.2134, creating an inconsistent exchange rate (6.2164 vs 6.2134) within the same valuation calculation.

**Error Fix:** Change D38 formula to "=C38/6.2164" to maintain consistent exchange rate usage throughout the model.

**Error Cell(s):** DCF Valuations, D42

**Error Type:** Incorrect cell reference  

**Error Explanation:** The stock option value conversion uses the wrong exchange rate. D42 uses C42/6.2134 while all other USD conversions in the model use 6.2164.

**Error Fix:** Change D42 formula to "=C42/6.2164" to maintain consistency with the exchange rate used throughout the rest of the model.

**Error Cell(s):** DCF Valuations, D45

**Error Type:** Incorrect cell reference

**Error Explanation:** The share price USD conversion uses the inconsistent exchange rate 6.2134 instead of 6.2164 that's used elsewhere in the model.

**Error Fix:** Change D45 formula to "=C45/6.2164" to use the consistent exchange rate.

**Error Cell(s):** Shares Outstanding, C11

**Error Type:** Formula omission error

**Error Explanation:** Cell C11 represents "Ordinary Shares Issued through IPO" but contains no value, which means the total shares calculation in C12 is missing the IPO shares component. This is a critical omission for an IPO valuation model.

**Error Fix:** Input the appropriate number of IPO shares to be issued, as indicated by the note "put your number here" in D11.