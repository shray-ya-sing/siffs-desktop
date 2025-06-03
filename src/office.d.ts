// src/office.d.ts
declare namespace ExcelScript {
    // This is a minimal declaration to satisfy the type checker
    // The actual implementation is provided by the Office Scripts runtime
    interface Workbook {
        getWorksheets(): any[];
        // Add other methods as needed
    }
    // Add other interfaces as needed
}