class StepLevelPrompts:

    @staticmethod
    def get_step_metadata_prompt():
        return """
        Please provide the sheet name and cell range that contains the relevant data for the current step.
        Include enough context around the target cells by adding at least 2 rows and columns to the range.
        This will be used to analyze the relevant section of the Excel file.
        
        IMPORTANT DATA HANDLING RULES:
        1. NEVER overwrite or modify existing data in the Excel file
        2. Only reference existing data, do not attempt to modify it
        3. If you need to add new data, it must be placed in a completely blank cell range
        4. Do not insert new rows or columns that would shift existing data
        
        Output your response as a dictionary with sheet names as keys and list of cell ranges as values:
        {"Sheet1": ["A1:B10", "C1:D5"], "Sheet2": ["A1:Z1000"]}
        """

    @staticmethod
    def get_step_instructions_prompt(step_number: str, step: str):
        return f"""
        Here is an overview of this step:{step}
        \n
        For step {step_number} in the sequence, create detailed instructions for implementing the element or action. 
        If the table is a new schedule, table, or cell region to be created, include a markdown version of the table in your response.
        The goal is to provide exact and detailed implementation instructions for maximum accuracy.
        
        CRITICAL IMPLEMENTATION RULES:
        1. NEVER overwrite or modify any existing data in the Excel file
        2. New data can ONLY be added in completely blank cell ranges
        3. Do not insert new rows or columns that would shift existing data
        4. If you need to reference existing data, do so without modifying it
        5. Clearly specify the exact cell range where new data should be placed
        
        Include a verification paragraph at the end that explains why the instructions are correct and serves as a self-check.
        The verification must confirm that no existing data will be overwritten and that any new data is placed in blank areas only.
        """

    @staticmethod
    def get_step_cell_formulas_prompt(step: str):
        return f"""
        Here are the instructions for this step:{step}
        \n
        To execute this step, generate the updated formulas to write to the excel file.
        
        CRITICAL DATA HANDLING RULES:
        1. NEVER overwrite or modify any existing non-blank cells
        2. Only write to cells that are completely empty
        3. If you need to reference existing data, do so without modifying it
        4. Do not insert new rows or columns that would shift existing data
        5. If you need to add new data, ensure it's placed in a completely blank area
        6. Double-check that your formulas only modify blank cells
        
        CORRECT EXCEL FORMULA GUIDELINES:
        
        AVERAGE: =AVERAGE(A1:A10) ✓ vs =AVERAGE(A1 A10) ✗ (missing comma)
        SUM: =SUM(A1:A10) ✓ vs =SUM A1:A10 ✗ (missing parentheses)
        VLOOKUP: =VLOOKUP("John", A2:B10, 2, FALSE) ✓ vs =VLOOKUP(John, A2:B10, 2, FALSE) ✗ (text without quotes)
        IF: =IF(A1>10, "Yes", "No") ✓ vs =IF A1>10 "Yes" "No" ✗ (missing syntax)
        SUMIF/SUMIFS: =SUMIF(A1:A10, ">10") ✓ vs =SUMIF(A1:A10 > 10) ✗ (incorrect syntax)
        INDEX-MATCH: =INDEX(B1:B10, MATCH("John", A1:A10, 0)) ✓ vs =INDEX(B1:B10, MATCH("John", A1:A10)) ✗ (missing match_type)
        COUNTIF/COUNTIFS: =COUNTIF(A1:A10, ">10") ✓ vs =COUNTIF("A1:A10", ">10") ✗ (range as text)
        TEXTJOIN: =TEXTJOIN(" ", TRUE, A1, B1) ✓ vs =A1 + " " + B1 ✗ (use & for text)
        DATE: =DATE(2023, 12, 31) ✓ vs =DATE("2023", "12", "31") ✗ (text instead of numbers)
        IFERROR: =IFERROR(VLOOKUP(...), "Not found") ✓ vs =IFERROR "VLOOKUP(...)" ✗ (formula as text)
        XLOOKUP: =XLOOKUP(A1, B1:B10, C1:C10, "Not found") ✓ vs =XLOOKUP(A1, B1:B10) ✗ (missing args)
        UNIQUE/FILTER: =UNIQUE(A1:A100) ✓ vs =UNIQUE("A1:A100") ✗ (range as text)
        OFFSET: =OFFSET(A1, 2, 3) ✓ vs =OFFSET("A1", 2, 3) ✗ (reference as text)
        HLOOKUP: =HLOOKUP("Q1", A1:Z4, 3, TRUE) ✓ vs =HLOOKUP(Q1, A1:Z4, 3, TRUE) ✗ (text without quotes)
        
        ADVANCED FORMULAS:
        
        CAGR (Compound Annual Growth Rate)
        Formula: =((Ending_Value/Starting_Value)^(1/Periods))-1
        Toggle Example: =IF(Toggle_UseCAGR=1, (End/Start)^(1/Periods)-1, (End-Start)/Start)
        
        SUMPRODUCT for Weighted Averages
        Formula: =SUMPRODUCT(Weights, Values) / SUM(Weights)
        
        OFFSET for Dynamic Ranges
        Formula: =SUM(OFFSET(Start_Cell, 0, 0, Height, Width))
        
        CHOOSE for Scenario Analysis
        Formula: =CHOOSE(Scenario_Number, Value1, Value2, Value3)
        
        INDIRECT for Flexible References
        Formula: =SUM(INDIRECT(Sheet_Name&"!A1:A10"))
        
        SUMIFS with Multiple Criteria
        Formula: =SUMIFS(Sum_Range, Criteria_Range1, Criteria1, [Criteria_Range2], [Criteria2], ...)
        
        XLOOKUP with Approximate Match
        Formula: =XLOOKUP(Lookup_Value, Lookup_Array, Return_Array, "", 1)
        
        EOMONTH for Period-End Dates
        Formula: =EOMONTH(Start_Date, Months)
        
        PMT for Loan Payments
        Formula: =PMT(Rate/12, Term*12, -Loan_Amount)
        
        NPV with Mid-Year Discounting
        Formula: =NPV(Rate, Cash_Flows)*(1+Rate)^IF(Mid_Year_Toggle=1, 0.5, 0)
        
        IRR with XIRR Toggle
        Formula: =IF(Toggle_Use_XIRR=1, XIRR(Values, Dates, Guess), IRR(Values, Guess))
        
        MATCH with Multiple Criteria
        Formula: =MATCH(1, (Criteria1_Range=Criteria1) * (Criteria2_Range=Criteria2), 0)


        Sheets property in the output should be a JSON like string mapping cell adress to updated formula. For example:
        {{
            "Sheet1": {{
                "A1": "=SUM(B1:B10)",
                "B1": "=A1*2"
            }},
            "Sheet2": {{
                "C1": "=AVERAGE(A1:A10)"
            }}
        }}

        DO NOT Group multiple cells together to create entries with cell ranges as keys like B87:B96': ['=Assumptions!A49', '=Assumptions!A50', '=Assumptions!A51'......].
        Make each key value pair entry for each cell, where the key represents the cell address of a SINGLE cell and the value the formula for only that SINGLE cell.
        """



    @staticmethod
    def decide_next_step_prompt() -> str:
        return """
        Based on the current implementation status and the task requirements, determine the next step that needs to be executed.
        
        Consider the following:
        1. The current step that was just completed (if any)
        2. The overall implementation sequence and progress
        3. Any dependencies between steps that must be maintained
        
        Return your response as a JSON object with the following structure:
        {
            "next_step_number": <int>,  // The step number to execute next (1-based index)
            "next_step": <str>,         // Brief description of the next step
            "all_steps_done": <bool>,   // True if all steps are completed
            "reasoning": <str>          // Very Brief explanation for choosing this next step
        }
        
        Important guidelines:
        - Only proceed to the next step if the current one is fully completed and verified
        - If there are any issues with the current step, return the same step number
        - If all steps are completed, set all_steps_done to True
        - Maintain the logical order of steps based on their dependencies
        - Consider any feedback or errors from previous steps when deciding
        
        Your response must be valid JSON that can be parsed by json.loads().
        """

