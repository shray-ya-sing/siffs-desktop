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
import { AlertTriangle, MapPin, Bug, Lightbulb, Wrench, AlertCircle } from "lucide-react"
import { Card, CardContent, CardHeader, CardTitle } from "../../components/ui/card"
import { Badge } from "../../components/ui/badge"
import Separator from "../../components/ui/separator"

interface ErrorCardProps {
  errorCells: string
  errorType: string
  errorExplanation: string
  errorFix: string
  critical?: boolean
}

export default function ErrorCard({
  errorCells,
  errorType,
  errorExplanation,
  errorFix,
  critical = true,
}: ErrorCardProps) {
  const isCritical = critical

  const cardStyles = isCritical ? "border-red-200 bg-red-50/50" : "border-yellow-200 bg-yellow-50/50"

  const titleStyles = isCritical ? "text-red-800" : "text-yellow-800"

  const iconColor = isCritical ? "text-red-600" : "text-yellow-600"

  const badgeVariant = isCritical ? ("destructive" as const) : ("secondary" as const)

  const badgeStyles = isCritical ? "" : "bg-yellow-100 text-yellow-800 border-yellow-300"

  const fixSectionStyles = isCritical ? "bg-green-50 border-green-200" : "bg-blue-50 border-blue-200"

  const fixTextStyles = isCritical ? "text-green-800" : "text-blue-800"

  const fixDescriptionStyles = isCritical ? "text-green-900 bg-green-100" : "text-blue-900 bg-blue-100"

  const fixIconColor = isCritical ? "text-green-600" : "text-blue-600"

  return (
    <Card className={`w-full max-w-2xl ${cardStyles}`}>
      <CardHeader className="pb-3">
        <CardTitle className={`flex items-center gap-2 ${titleStyles}`}>
          {isCritical ? <AlertTriangle className="h-5 w-5" /> : <AlertCircle className="h-5 w-5" />}
          {isCritical ? "Critical Formula Error" : "Formula Warning"}
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex items-center gap-2">
          <MapPin className={`h-4 w-4 ${iconColor}`} />
          <span className="text-sm font-medium text-gray-700">Error Cell(s):</span>
          <Badge variant={badgeVariant} className={`font-mono ${badgeStyles}`}>
            {errorCells}
          </Badge>
        </div>

        <Separator />

        <div className="flex items-start gap-2">
          <Bug className={`h-4 w-4 ${iconColor} mt-0.5`} />
          <div className="flex-1">
            <span className="text-sm font-medium text-gray-700">Error Type:</span>
            <p className="text-sm text-gray-900 mt-1">{errorType}</p>
          </div>
        </div>

        <div className="flex items-start gap-2">
          <Lightbulb className="h-4 w-4 text-amber-600 mt-0.5" />
          <div className="flex-1">
            <span className="text-sm font-medium text-gray-700">Error Explanation:</span>
            <p className="text-sm text-gray-900 mt-1">{errorExplanation}</p>
          </div>
        </div>

        <div className={`flex items-start gap-2 p-3 rounded-lg border ${fixSectionStyles}`}>
          <Wrench className={`h-4 w-4 ${fixIconColor} mt-0.5`} />
          <div className="flex-1">
            <span className={`text-sm font-medium ${fixTextStyles}`}>
              {isCritical ? "Error Fix:" : "Suggested Fix:"}
            </span>
            <p className={`text-sm mt-1 font-mono px-2 py-1 rounded ${fixDescriptionStyles}`}>{errorFix}</p>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
