import { AlertTriangle, MapPin, Bug, Lightbulb, Wrench } from "lucide-react"
import { Card, CardContent, CardHeader, CardTitle } from "../../components/ui/card"
import { Badge } from "../../components/ui/badge"
import Separator from "../../components/ui/separator"

interface ErrorCardProps {
  errorCells: string
  errorType: string
  errorExplanation: string
  errorFix: string
}

export default function ErrorCard({ errorCells, errorType, errorExplanation, errorFix }: ErrorCardProps) {
  return (
    <Card className="w-full max-w-2xl border-red-200 bg-red-50/50">
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center gap-2 text-red-800">
          <AlertTriangle className="h-5 w-5" />
          Formula Error Detected
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex items-center gap-2">
          <MapPin className="h-4 w-4 text-red-600" />
          <span className="text-sm font-medium text-gray-700">Error Cell(s):</span>
          <Badge variant="destructive" className="font-mono">
            {errorCells}
          </Badge>
        </div>

        <Separator />

        <div className="flex items-start gap-2">
          <Bug className="h-4 w-4 text-red-600 mt-0.5" />
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

        <div className="flex items-start gap-2 bg-green-50 p-3 rounded-lg border border-green-200">
          <Wrench className="h-4 w-4 text-green-600 mt-0.5" />
          <div className="flex-1">
            <span className="text-sm font-medium text-green-800">Error Fix:</span>
            <p className="text-sm text-green-900 mt-1 font-mono bg-green-100 px-2 py-1 rounded">{errorFix}</p>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
