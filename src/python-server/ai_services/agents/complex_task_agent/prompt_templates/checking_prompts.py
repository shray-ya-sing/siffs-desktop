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
        DO NOT START GENERATING COMPLETIONS FOR THE NEXT STEP. ONLY EVALUATE THE SUCCESSFUL COMPLETION OF YOUR CURRENT STEP. 
        If the step was fully successfully edited, and there is nothing wrong, you can proceed onto the next step, return true, 
        and a summary of the edit evaluation. If the edit was partially or not at all successful, you MUST consider reverting the 
        edits you just made and trying again. Return false and a summary of the edit evaluation as a dict object 
        {
            success: [true or false],
            rationale: [summary of the edit evaluation]
        }
        """
        return CHECK_EDIT_SUCCESS_PROMPT + '\n-------------------------------------\n' + REVERSION_REQUEST

    @staticmethod
    def decide_revert_prompt():
        return """
        Do not proceed immediately to the next step. If there are corrections in the edit execution, you MAY revert the edit and 
        redo it. Assuming your edit has been fully reverted i.e. all the formulas you generated for the cells you assigned them to 
        have been fully reverted to their original state. DO YOU WISH TO REVERT THE EDIT AND TRY TO IMPLEMENT IT AGAIN OR PROCEED 
        WITH THE CURRENT STATE? Return true to revert and false to not. If you wish to revert, also return the cell range of the cells that should be reverted to their prior values. 
        """

    @staticmethod
    def decide_retry_prompt():
        return """
        You have successfully reverted the edit in the specified cells. Do you wish to retry the edit or proceed to the next step? If you wish to retry, 
        you can view the metadata of the excel file for the cell region you wish to edit. Return a dict with the sheet name and 
        cell range you wish to view. Remember, to get context, you should get at least 2 rows and columns outside of the cell range 
        you wish to edit so you can view the full metadata. Which cell range metadata do you wish to view for your edit? 
        """

    @staticmethod
    def retry_edit_data_prompt(instructions,excel_metadata, error_comments):
        return f"""
        Here is the metadata after the reversion i.e. restoring to the original state. 
        Based on this updated metadata, for the step in the sequence, create detailed instructions for the implementation of the 
        element or action. If the table is a new schedule or table or cell region to be created, create a markdown version of the 
        table in your text response. The goal is to create as exact and detailed instructions for the implementation of the step as 
        possible, for maximum accuracy. In your response, include a verification paragraph at the end that explains why the 
        instructions you set out are correct and acts as a check on your work.
        REMEMBER NOT TO REPEAT YOUR PRIOR MISTAKE, read your error commentary carefully and generate the instructions in a way that 
        corrects your prior mistake and implements what is truly required.
        ----------------ORIGINAL INSTRUCTIONS:
        {instructions}
        -----------------METADATA:
        {excel_metadata}
        -----------------COMMENTS:    
        {error_comments}
        """

    @staticmethod
    def check_element_location_prompt():
        return """
        Determine if any of your suggestions overlap with existing content and fix the locations of the new elements if any of the 
        new elements are overlapping with existing filled cells. You are not allowed to overwrite or add new rows in between existing 
        elements, so anything to be built from scratch can only be built in cell regions that are COMPLETELY EMPTY.
        """

    @staticmethod
    def get_retry_cell_formulas_prompt(instructions,excel_metadata, error_comments):
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
 
        ----------------ORIGINAL INSTRUCTIONS:
        {instructions}
        -----------------METADATA:
        {excel_metadata}
        -----------------COMMENTS:    
        {error_comments}
        """
