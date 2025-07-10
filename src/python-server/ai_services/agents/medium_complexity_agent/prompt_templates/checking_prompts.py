class CheckingPrompts:
    @staticmethod
    def get_updated_metadata_prompt():
        return """
        you need to look at the updated excel contents to determine if the formulas you generated were correctly applied. 
        Give me the sheet name and exact cell range that you want to extract the formulas in so you can look at the updated values. 
        Extract not only the cells you generated edits for but the context around them, so add at least 2 rows and columns to the 
        cell range so you can view the context as well to determine if the edit was successfully executed, or if it resulted in a 
        malformed or wrongfully edited file. 
        output result in a sheets property that should be a json like string like {"Sheet1": ["A1:B10", "C1:D5"], "Sheet2": ["A1:Z1000"]}
        """

    @staticmethod
    def check_edit_success_prompt(excel_metadata):
        CHECK_EDIT_SUCCESS_PROMPT = f"""
        Here is the updated metadata for the range you requested on the sheet you requested, examine it and determine if your edit 
        was correctly executed or did not get executed properly:

        {excel_metadata}
        """

        REVERSION_REQUEST = """
        If the step was fully successfully edited, and there is nothing wrong, you can proceed onto the next step, return true, 
        and a summary of the edit evaluation. If the edit was partially or not at all successful, you MUST re-generate the correct formulas for the incorrect cells. Return false and a summary of the edit evaluation as a dict object 
        {
            success: [true or false],
            rationale: [summary of the edit evaluation]
            correct_formulas: [pipe delimited markdown string of a nested dictionary mapping sheet names to cell formulas]
            like, sheet_name: [Name of the sheet]| A1, "=SUM(B1:B10)" | B1, "Text value" | C1, 123 | sheet_name: [Next sheet name]| D5, "=AVERAGE(A1:A10)" | E5, "Another value"
        }
        """

        FORMULAS_PROMPT = CheckingPrompts.get_retry_cell_formulas_prompt()

        return CHECK_EDIT_SUCCESS_PROMPT + '\n----------------\n' + FORMULAS_PROMPT + '\n----------------\n' + REVERSION_REQUEST

   
    @staticmethod
    def get_retry_cell_formulas_prompt():
        return f""" 
        Generate updated cell formulas for cells in the excel sheet for this retry attempt.        
        FORMAT YOUR RESPONSE AS FOLLOWS:
        
        sheet_name: [Name of the sheet]| A1, "=SUM(B1:B10)" | B1, "Text value", b=true, it=true, num_fmt="#,000.0", sz="12", st="calibri", font="#000000", fill="#0f0f0f" | C1, 123 

        RETURN ONLY THIS - DO NOT ADD ANYTHING ELSE LIKE STRING COMMENTARY, REASONING, EXPLANATION, ETC. 
        Just return the pipe-delimited markdown containing cell formulas and formatting properties in the specified format.

        RULES:
        1. Start each sheet with 'sheet_name: [exact sheet name]' followed by a pipe (|).
        2. List each cell update as: [cell_reference], "[formula_or_value]", [formatting properties if any].
        3. Formatting properties should be included ONLY if necessary to continue a pattern observed in neighboring cells.
        4. Formatting properties must be in this exact order: bold (b), italic (it), number format (num_fmt), font size (sz), font style (st), font color (font), and cell fill color (fill).
        5. Use keyword identifiers: b, it, num_fmt, sz, st, font, fill to denote properties.
        6. Separate multiple cell updates with pipes (|).
        7. Always enclose formulas, text values, and number formats in double quotes.
        8. Numbers can be written without quotes.
        9. Include ALL cells that need to be written.
        10. NEVER modify or reference non-existent cells.
        
        EXAMPLES:
        
        sheet_name: Income Statement| B5, "=SUM(B2:B4)" | B6, 1000, b=true | B7, "=B5-B6", it=true, font="#0000FF" | sheet_name: Assumptions| B2, 0.05 | B3, 1.2, sz="10" | C3, "=B3*1.1", num_fmt="#,##0.00"

        BAD EXAMPLES:
        - sheet_name: Income Statement B5, "=SUM(B2:B4)"  # Missing pipe after sheet name
        - sheet_name: Income Statement | B5, =SUM(B2:B4)   # Formula not in quotes
        - sheet_name: Income Statement | B5 SUM(B2:B4)     # Missing comma after cell reference
        
        ADDITIONAL NOTES:
        - When parsing, the system will look for properties based on the keyword identifiers (b, it, num_fmt, sz, st, font, fill) and handle them based on their existence and values after the '=' sign.
        """
