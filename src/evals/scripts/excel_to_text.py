import pandas as pd
from pathlib import Path

def excel_to_error_format(excel_path, output_path=None):
    """
    Convert Excel error data to the specified text format.
    
    Args:
        excel_path (str): Path to the Excel file
        output_path (str, optional): Path to save the output text file. If None, prints to console.
    """
    try:
        # Read the Excel file
        df = pd.read_excel(excel_path)
        
        # Initialize output text
        output = []
        
        # Process each row in the Excel file
        for _, row in df.iterrows():
            error_text = (
                f"Error Cell(s): {row.get('Tab', '')}, {row.get('Cell Reference', '')}\n"
                f"Error Type: {row.get('Error Type', '')}\n"
                f"Error Explanation: {row.get('Explanation', '')}\n"
                f"Error Fix: {row.get('Fix', '')}\n"
            )
            output.append(error_text)
        
        # Combine all error texts
        result = "\n".join(output)
        
        # Save to file or print to console
        if output_path:
            with open(output_path, 'w') as f:
                f.write(result)
            print(f"Output saved to {output_path}")
        else:
            print("\n" + "="*50 + "\n")
            print(result)
            print("="*50 + "\n")
            
    except Exception as e:
        print(f"An error occurred: {str(e)}")

# Example usage:
if __name__ == "__main__":
    excel_file = "path_to_your_excel_file.xlsx"  # Update this path
    output_file = "output_errors.txt"  # Optional: specify output file path
    excel_to_error_format(excel_file, output_file)