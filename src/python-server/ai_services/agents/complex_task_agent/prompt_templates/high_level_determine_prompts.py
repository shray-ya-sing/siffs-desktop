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
        Check what foundation is already laid out in the model, and what, if anything, remains to be done. 
        We do not need to repeat what we already have, we just need to determine what remains for us to do. 
        Output your response in a text paragraph summary -- first list what already exists in the excel, then summarize what exists 
        that is useful for the request in the prompt, then list what remains to be done. 

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
        """

    @staticmethod
    def get_implementation_sequence_prompt():
        return """
        Based on your understanding of what elements, rows and cells need to link together and how, create the exact sequence in which 
        you will go about implementing the actions to construct new elements and link or modify existing ones. Clearly break out each 
        element in the sequence and set out the sequence as a numbered list, listing the name of the element and the description of 
        what you need to do to implement that element in the sub-step.
        "

