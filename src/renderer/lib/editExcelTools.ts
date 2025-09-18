/*
 * Siffs - Fast File Search Desktop Application
 * Copyright (C) 2025  Siffs
 * 
 * Contact: github.suggest277@passinbox.com
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see <https://www.gnu.org/licenses/>.
 */
import { ComponentType, SVGProps } from 'react';
import { Globe, Search, FileText, ClipboardList, BarChart2 } from "lucide-react"

export type CreateExcelTool = {
  id: string
  name: string
  description: string
  category: string
  icon: ComponentType<SVGProps<SVGSVGElement> & { className?: string }>;
  color: string;
  onStart?: () => void
}

export const categories = [
  "Run Sensitivities or Cases",
  "Version Up and Update Values",
  "Reformat or Fix Formatting",
  "Build Charts or Visualizations Based on Data in your Existing Excel"
] as const

const tools: CreateExcelTool[] = [
  {
    id: "run-sensitivity",
    name: "Run Sensitivities or Cases",
    description: "Run sensitivities or cases on your Excel model and build sensitivity tables for new cases.",
    category: "Run Sensitivities or Cases",
    icon: BarChart2,
    color: "#6D28D9", // Darker Purple (from #8B5CF6)
  },
  {
    id: "version-up-and-update-values",
    name: "Version Up and Update Values",
    description: "Version up and update values in your Excel model based on new commercial, financial or operational diligence documents.",
    category: "Version Up and Update Values",
    icon: Globe,
    color: "#1D4ED8" // Darker Blue (from #3B82F6)
  },
  {
    id: "aggregate-data-into-new-excel",
    name: "Aggregate Data into New Excel",
    description: "Aggregate data from multiple Excel files into a new Excel model.",
    category: "Aggregate Data into New Excel",
    icon: FileText,
    color: "#0D9488" // Darker Green (from #10B981)
  },
  {
    id: "quick-lbo",
    name: "Quick LBO",
    description: "Create a quick LBO analysis for an initial deal screening based on your data and reference templates.",
    category: "Quick LBO",
    icon: ClipboardList,
    color: "#D97706" // Darker Amber (from #F59E0B)
  }
]

export const allTools = [...tools]