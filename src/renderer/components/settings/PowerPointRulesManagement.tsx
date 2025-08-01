import React, { useState, useEffect } from 'react';
import { webSocketService } from '../../services/websocket/websocket.service';
import { Button } from '../ui/button';
import { Textarea } from '../ui/textarea';
import { useToast } from '../ui/use-toast';

interface PowerPointRulesData {
  rules: string;
  lastUpdated?: string;
}

interface PowerPointRulesResponse {
  status: 'success' | 'error';
  data?: PowerPointRulesData;
  message?: string;
}

export function PowerPointRulesManagement() {
  const [rules, setRules] = useState<string>('');
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [isSaving, setIsSaving] = useState<boolean>(false);
  const [lastUpdated, setLastUpdated] = useState<string>('');
  const { toast } = useToast();

  // Load rules on component mount
  useEffect(() => {
    loadRules();
    
    // Set up WebSocket listeners
    const handleRulesResponse = (message: any) => {
      console.log('PowerPoint rules response received:', message);
      
      if (message.type === 'POWERPOINT_RULES_STATUS') {
        setIsLoading(false);
        // Backend sends rules directly in the message
        setRules(message.rules || '');
        setLastUpdated(message.lastUpdated || '');
      } else if (message.type === 'POWERPOINT_RULES_ERROR') {
        setIsLoading(false);
        setIsSaving(false);
        toast({
          title: "Error",
          description: message.error || "An error occurred",
          variant: "destructive",
        });
      } else if (message.type === 'POWERPOINT_RULES_SET_RESPONSE') {
        setIsSaving(false);
        const response = message.data as PowerPointRulesResponse;
        
        if (response.status === 'success') {
          toast({
            title: "Success",
            description: "Global PowerPoint formatting rules saved successfully!",
          });
          setLastUpdated(new Date().toISOString());
        } else {
          toast({
            title: "Error",
            description: response.message || "Failed to save PowerPoint formatting rules",
            variant: "destructive",
          });
        }
      } else if (message.type === 'POWERPOINT_RULES_REMOVED') {
        setIsSaving(false);
        // Backend sends success message directly
        setRules('');
        setLastUpdated('');
        toast({
          title: "Success",
          description: message.message || "Global PowerPoint formatting rules cleared successfully!",
        });
      }
    };

    webSocketService.on('POWERPOINT_RULES_STATUS', handleRulesResponse);
    webSocketService.on('POWERPOINT_RULES_SET_RESPONSE', handleRulesResponse);
    webSocketService.on('POWERPOINT_RULES_REMOVED', handleRulesResponse);
    webSocketService.on('POWERPOINT_RULES_ERROR', handleRulesResponse);

    return () => {
      webSocketService.off('POWERPOINT_RULES_STATUS', handleRulesResponse);
      webSocketService.off('POWERPOINT_RULES_SET_RESPONSE', handleRulesResponse);
      webSocketService.off('POWERPOINT_RULES_REMOVED', handleRulesResponse);
      webSocketService.off('POWERPOINT_RULES_ERROR', handleRulesResponse);
    };
  }, [toast]);

  const loadRules = () => {
    setIsLoading(true);
    webSocketService.sendMessage({
      type: 'POWERPOINT_RULES_GET',
      timestamp: new Date().toISOString(),
      data: {}
    });
  };

  const saveRules = () => {
    if (!rules.trim()) {
      toast({
        title: "Warning",
        description: "Please enter formatting rules before saving",
        variant: "destructive",
      });
      return;
    }

    setIsSaving(true);
    webSocketService.sendMessage({
      type: 'POWERPOINT_RULES_SET',
      timestamp: new Date().toISOString(),
      data: {
        rules: rules.trim()
      }
    });
  };

  const clearRules = () => {
    if (!rules.trim()) {
      toast({
        title: "Info",
        description: "No rules to clear",
      });
      return;
    }

    setIsSaving(true);
    webSocketService.sendMessage({
      type: 'POWERPOINT_RULES_REMOVE',
      timestamp: new Date().toISOString(),
      data: {}
    });
  };

  const handleRulesChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setRules(e.target.value);
  };

  const getExampleRules = () => {
    const exampleRules = `Font Formatting:
- Use "Calibri" as the primary font family for all text
- Title slides: 24pt font size, bold formatting
- Header text: 18pt font size, bold formatting  
- Body text: 12pt font size, regular weight
- Use #1f4e79 for headers and titles
- Use #333333 for body text

Shape Formatting:
- Use #f8f9fa for content box backgrounds
- Use #dee2e6 for shape borders with 1pt width
- Apply rounded corners (5pt radius) to all rectangles
- Center-align titles and headers
- Left-align body content

Color Palette:
- Primary brand color: #007acc
- Secondary color: #6c757d
- Success color: #28a745
- Warning color: #ffc107
- Error color: #dc3545

Layout Guidelines:
- Maintain 20pt margins from slide edges
- Use consistent spacing of 15pt between elements
- Position titles at top=50pt from slide top
- Position main content starting at top=120pt`;
    
    setRules(exampleRules);
  };

  return (
    <div className="space-y-6">
      <div className="text-center">
        <h2 className="text-2xl font-light text-white mb-2">Global PowerPoint Formatting Rules</h2>
        <p className="text-gray-400 font-light">
          Set global formatting rules that will be applied to all PowerPoint edits and generations.
          These rules ensure consistent styling across your presentations.
        </p>
      </div>

      <div className="space-y-4">
        <div className="flex justify-between items-center">
          <label htmlFor="powerpoint-rules" className="text-gray-300 font-light text-sm">
            Formatting Rules
          </label>
          <div className="flex gap-2">
            <Button
              onClick={getExampleRules}
              variant="outline"
              size="sm"
              className="text-xs bg-gray-800/50 border-gray-700/50 text-gray-300 hover:bg-gray-700/50 hover:text-white"
            >
              Load Example
            </Button>
            {rules.trim() && (
              <Button
                onClick={clearRules}
                variant="destructive"
                size="sm"
                disabled={isSaving}
                className="text-xs"
              >
                {isSaving ? 'Clearing...' : 'Clear Rules'}
              </Button>
            )}
          </div>
        </div>

        <Textarea
          id="powerpoint-rules"
          value={rules}
          onChange={handleRulesChange}
          placeholder="Enter your global PowerPoint formatting rules here...

Example:
Font Formatting:
- Use 'Calibri' font family for all text
- Title slides: 24pt, bold
- Body text: 12pt, regular
- Use #1f4e79 for headers

Shape Formatting:
- Use #f8f9fa backgrounds for content boxes
- Apply 1pt borders with #dee2e6 color
- Center-align titles, left-align body text

Layout Guidelines:
- 20pt margins from slide edges
- 15pt spacing between elements"
          className="min-h-[300px] bg-gray-800/50 border-gray-700/50 text-white placeholder-gray-500 focus:border-gray-600 focus:ring-2 focus:ring-gray-600/50 resize-none font-mono text-sm leading-relaxed"
          disabled={isLoading || isSaving}
        />

        {lastUpdated && (
          <p className="text-xs text-gray-500 text-right">
            Last updated: {new Date(lastUpdated).toLocaleString()}
          </p>
        )}
      </div>

      <div className="flex justify-center gap-4 pt-4">
        <Button
          onClick={saveRules}
          disabled={isSaving || isLoading || !rules.trim()}
          className="bg-gray-800/70 hover:bg-gray-700/80 text-white border border-gray-700/50 px-8 py-3 rounded-full font-light transition-all duration-300 shadow-lg hover:shadow-xl"
        >
          {isSaving ? 'Saving...' : 'Save Rules'}
        </Button>
        
        <Button
          onClick={loadRules}
          disabled={isLoading || isSaving}
          className="bg-gray-800/70 hover:bg-gray-700/80 text-white border border-gray-700/50 px-8 py-3 rounded-full font-light transition-all duration-300 shadow-lg hover:shadow-xl"
        >
          {isLoading ? 'Loading...' : 'Refresh'}
        </Button>
      </div>

      <div className="bg-gray-800/30 border border-gray-700/30 rounded-xl p-4 mt-6">
        <h3 className="text-sm font-medium text-gray-300 mb-2">💡 How it works:</h3>
        <ul className="text-xs text-gray-400 space-y-1 leading-relaxed">
          <li>• These rules will be automatically applied to all PowerPoint editing operations</li>
          <li>• Rules are sent to the AI along with your specific edit instructions</li>
          <li>• Use natural language to describe fonts, colors, layouts, and styling preferences</li>
          <li>• Rules are saved per user and persist across sessions</li>
          <li>• You can override global rules with specific instructions in individual requests</li>
        </ul>
      </div>
    </div>
  );
}
