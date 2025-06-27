FINAL_EVALUATOR_PROMPT = 
"""
Evaluate the full excel file to determine if all your edits were implemented correctly, or if there are still errors remaining. n
Evaluate if the file has been edited to successfully fulfil the user's requirements.
If the file is fully complete and all the requirements of the user's original request are satisfied, inform the user that the task is complete.
"""

def get_final_success_prompt(final_excel_metadata):
    return f"{FINAL_EVALUATOR_PROMPT}\n\nHere is the full, final excel metadata:\n{final_excel_metadata}"