NUMBER_FORMATS = """General Numbers
•  "General" - Default Excel format, good for basic integers
•  "0" - Whole numbers without decimals
•  "#,##0" - Whole numbers with thousands separators

Financial Figures
•  "#,##0" - Large whole numbers (e.g., revenue in thousands)
•  "#,##0.0" - One decimal place with thousands separator
•  "#,##0.00" - Two decimal places with thousands separator
•  "$#,##0" - Currency without decimals
•  "$#,##0.00" - Standard currency format
•  "($#,##0)" - Negative numbers in parentheses (accounting style)
•  "_($* #,##0_);_($* (#,##0);_($* \"-\"??_);_(@_)" - Full accounting format

Percentages
•  "0%" - Whole percentage (e.g., 25%)
•  "0.0%" - One decimal place (e.g., 25.5%)
•  "0.00%" - Two decimal places (e.g., 25.50%)
•  "#,##0.0%" - Large percentages with thousands separator

Decimals
•  "0.0" - One decimal place
•  "0.00" - Two decimal places
•  "0.000" - Three decimal places
•  "#,##0.0" - One decimal with thousands separator
•  "#,##0.00" - Two decimals with thousands separator

Financial Multiples
•  "0.0x" - Multiples with one decimal (e.g., 2.5x)
•  "0.00x" - Multiples with two decimals (e.g., 2.50x)
•  "#,##0.0x" - Large multiples with separator

Years in Financial Schedules
•  "0" - Simple year format (e.g., 2024)
•  ""Year "0" - With "Year" prefix (e.g., Year 2024)
•  ""FY"0" - Fiscal year format (e.g., FY2024)
•  "0"/"00" - Fiscal year range (e.g., 2024/25)

Special Financial Formats
•  "[>999999] #,##0,,"M";[>999] #,##0,"K";#,##0" - Auto-scale to M/K
•  "#,##0_);(#,##0)" - Parentheses for negatives, space for positives
•  "#,##0.0_);[Red](#,##0.0)" - Red text for negatives
•  ""$"#,##0.0,,"M"" - Millions format ($25.5M)
•  ""$"#,##0,,"M";[Red]("$"#,##0,,"M")" - Millions with red negatives

Basis Points
•  "0"bp"" - Basis points (e.g., 250bp)
•  "#,##0"bp"" - Large basis points with separator

Ratios
•  "0.0:1" - Ratio format (e.g., 2.5:1)
•  "0.00:1.00" - Detailed ratio format

Date Formats
•  Short Date: m/d/yyyy or mm/dd/yyyy
•  Long Date: dddd, mmmm d, yyyy
•  Custom Date: Customizable formats using elements like yyyy, mmm, dd

Day Formats
•  Day Only: d or dd (shows the day of the month)
•  Day Name Only: ddd or dddd (shows the name of the day, e.g., Mon or Monday)

Common Financial Model Patterns
"""

DEFAULT_NUMBER_FORMATS = """
General Large Numbers, more than 3 digits:    #,##0
General Small Numbers, less than 3 digits:    0
General Decimal:          0.0
Margins/Percentages:      0.0%
Multiples (P/E, EV/EBITDA): 0.00x
Growth Rates:             0.0%
Years:                    0
USD Currency Small:       $#,##0
USD Currency Detailed:    $#,##0.00
Large USD Currency:       $#,##0,,"M"
Financial figures (negative numbers in parenthesis, dashes for 0s): _(* #,##0_);_(* (#,##0);_(* "-"_);_(@_)
Financial figures with USD currency: _($* #,##0_);_($* (#,##0);_($* "-"_);_(@_)
Fiscal year format (e.g., FY2025): "FY"0
Expected year format (e.g., 2025E): 0"E"
Actual year format (e.g., 2025A): 0"A"
Plain Year (e.g., 2025): 0
Year with "Year" prefix (e.g., Year 2025): "Year "0
Short Date (e.g., 07/16/2025): m/d/yyyy or mm/dd/yyyy
Long Date (e.g., Thursday, July 16, 2025): dddd, mmmm d, yyyy
Day Only (e.g., 16): d or dd
Day Name Only (e.g., Thursday): ddd or dddd
Custom Date: Customizable formats using elements like yyyy, mmm, dd
"""
