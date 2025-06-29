class HighLevelDeterminePrompts:
    @staticmethod
    def get_request_essence_prompt():
        return """
        Extract the main task being specified in no more than 2 sentences. 
        Then break down 3-5 main steps required to complete the task. 
        All tasks relate to building or editing an excel financial model and will relate to the three main financial statements, 
        the Income Statement, the Balance Sheet, and the Cash Flow Statement. 
        Tasks may require setup, editing, or completion of one or more statements, as well as possible work on supporting schedules, 
        sections and subsections that make these templates. 
        Prompts will be long, information dense and require complex work. 
        Your job is to break down these complicated tasks into simpler steps and tasks that encapsulate the core of what the prompt 
        is requesting without getting too bogged into the details of how to implement each task. 
        In other words, you are to build high level summary of what you need to do to complete the request.
        """

    @staticmethod
    def get_excel_status_prompt(excel_metadata):
        return f"""
        Based on the excel file metadata supplied to you, determine the current status of the excel file and status of completion 
        for each step to be done in building the model. 
        
        IMPORTANT RULES:
        1. NEVER overwrite or modify any existing data, formulas, or structure with new or unrelated data unless specfied in user request-- only modify the formulas and links if necessary to integrate with new edits
        2. Only add to or link to existing elements - never replace them, unless specified in user request
        3. If an assumptions/control panel tab exists, use it instead of creating a new one
        4. Keep related schedules and statements together on the same tab when possible
        5. Don't break the existing infrastructure of the model
        
        Check what foundation is already laid out in the model, and what, if anything, remains to be done. 
        We do not need to repeat what we already have, we just need to determine what remains for us to do. 
        
        Output your response in a text paragraph summary:
        1. List what already exists in the excel that's relevant to the request
        2. Summarize what exists that can be utilized
        3. List only what remains to be done, considering the existing structure

        {excel_metadata}
        """

    @staticmethod
    def get_model_architecture_prompt():
        return """
        Different financial models have different architectures. Most three statement models are interlinked on separate tabs, 
        sometimes with the three statements linked together on the same tab. Some models have each supporting schedule, whether PPE, 
        Debt, Working Capital, Operations and Revenue, Or Cash on a different tab. Some models have all the supporting schedules and 
        financial models linked together on the same tab. Some models put financial statements and schedules on the same tab, while 
        DCF valuation is on a separate tab, LBO valuation is on a separate tab, or IRR analysis is on a separate tab. Other models 
        have all the tables and schedules all on the same tab. Based on your analysis of the remaining steps to completion of the 
        model, you need to decide the architecture of how you are going to build any new tables, or link together any existing tables. 
        Create a list of New Elements (not started yet, require full work till completion) and their locations on tabs, and a list of 
        Partially complete elements (partially done but need more work to fulfill the task request) and their locations on tabs in the model.
        Analyze the existing model structure and plan how to implement the required changes while following these CRITICAL RULES:
        
        DATA PRESERVATION RULES:
        1. NEVER overwrite or modify any existing data, formulas, or structure
        2. Only add to or link to existing elements - never replace them
        3. If an element already exists, find a way to use it rather than creating a duplicate
        4. Follow the architectural pattern set up in the model, if any
        
        EFFICIENCY GUIDELINES:
        1. Use existing tabs and structures whenever possible
        2. Keep related schedules and statements together on the same tab
        3. Add new schedules below existing content rather than creating new tabs
        4. If an assumptions/control panel exists, use it instead of creating a new one
        5. Link to existing data sources rather than duplicating them
        
        Based on these rules and your analysis of the remaining steps, plan how to implement the required changes:
        1. List New Elements needed (not started yet) and their optimal locations
        2. List Partially Complete elements that need modification
        3. For each element, specify whether it should be added to an existing tab or needs a new tab (only if absolutely necessary)
        4. Identify any existing elements that can be reused or linked to
        
        Remember: The goal is to maintain a clean, efficient model structure with minimal redundancy.
        """

    @staticmethod
    def get_implementation_sequence_prompt():
        return """
        Create a detailed implementation sequence for the financial model, following these CRITICAL RULES:
        
        DATA PRESERVATION RULES:
        1. NEVER overwrite or modify any existing data, formulas, or structure
        2. Only add to or link to existing elements - never replace them
        3. If an element exists, find a way to use it rather than creating a duplicate
        
        EFFICIENCY GUIDELINES:
        1. Reuse existing tabs and structures whenever possible
        2. Add new schedules below existing content rather than creating new tabs
        3. Link to existing data sources rather than duplicating them
        4. Keep related schedules and statements together on the same tab
        
        Based on these rules, create the exact sequence for implementation. For each step, include:
        1. What existing elements will be used (if any)
        2. Where new elements will be placed (prefer existing tabs)
        3. How elements will be linked together
        4. Any dependencies between steps
        
        Return a JSON object with this exact structure:
        {
            "implementation_sequence": "Description of the sequence, listed step by step in a numbered text paragraph",
            "steps": [
                {
                    "step_number": 1,
                    "description": "Step description, including what existing elements are used and where new ones will be placed",
                    "location": "Specify tab and approximate cell range if applicable",
                    "links_to_existing": ["List any existing elements this step will link to"]
                }
            ]
        }
        """

