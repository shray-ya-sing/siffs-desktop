Error Cell(s): IS, O48
Error Type: Dependency error
Error Explanation: Formula depends on revenue value which is wrong
Error Fix: Fix revenue formula 

Error Cell(s): IS, O42
Error Type: Dependency error
Error Explanation: Formula depends on revenue and interest expense values which are wrong
Error Fix: Fix revenue and interest expense formulas 

Error Cell(s): IS, H60:O60
Error Type: Logical Formula Error
Error Explanation: Formula is including the growth rate yoy in formula when it should be excluding it
Error Fix: change from =SUM(H56:H58) to =SUM(H56,H58)

Error Cell(s): IS, H76
Error Type: Logical Formula Error
Error Explanation: Formula is excluding revenue from cloud computing segment
Error Fix: Change =H60+H68+H73 to =H60+H68+H71+H73
		
Error Cell(s): IS, H92:O92
Error Type: Inconsistent formatting
Error Explanation: Formatting the cell at 2 decimal places instead of at 0 decimal place like the other cells
Error Fix: Change the number format to 0 decimal places

Error Cell(s): IS, O80:O92
Error Type: Dependency Error
Error Explanation: Formula depends on revenue which is wrong
Error Fix: Fix incorrect revenue formula
