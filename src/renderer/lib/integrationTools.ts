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
import { Globe, Search, FileText, ClipboardList, BarChart2, Layout, Database } from "lucide-react"
import { ComponentType, SVGProps } from 'react';

export type Tool = {
  id: string
  name: string
  description: string
  category: string
  icon: ComponentType<SVGProps<SVGSVGElement> & { className?: string }>;
  color: string;
  onStart?: () => void
}

export const categories = [
  "Excel Model Audit",
  "Excel Model QA",
  "Edit an Excel Model", 
  "Create an Excel Model",
] as const

const tools: Tool[] = [
  {
    id: "excel-model-audit",
    name: "Excel Model Audit",
    description: "Comprehensive auditing and error checking for Excel financial models, including formula validation, error tracing, and best practice analysis.",
    category: "Excel Model Audit",
    icon: BarChart2,
    color: "#6D28D9", // Darker Purple (from #8B5CF6)
  },
  {
    id: "excel-model-qa",
    name: "Excel Model QA",
    description: "Question answering and analysis to understand and evaluate Excel financial models.",
    category: "Excel Model QA",
    icon: Globe,
    color: "#1D4ED8" // Darker Blue (from #3B82F6)
  },
  {
    id: "edit-excel-model",
    name: "Edit an Excel Model",
    description: "Edit an existing Excel model.",
    category: "Edit an Excel Model",
    icon: FileText,
    color: "#0D9488" // Darker Green (from #10B981)
  },
  {
    id: "create-excel-model",
    name: "Create an Excel Model",
    description: "Create a new Excel model from scratch.",
    category: "Create an Excel Model",
    icon: Database,
    color: "#D97706" // Darker Amber (from #F59E0B)
  }
]

export const allTools = [...tools]
