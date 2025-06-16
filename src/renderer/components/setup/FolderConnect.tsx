import { useState, useRef, useEffect } from "react";
import { FolderOpen, FileText, Folder, Check } from "lucide-react";
import FileDiscoveryProgress from "./FileDiscoveryProgress"
import { v4 as uuidv4 } from 'uuid';
import { webSocketService } from '../../services/websocket/websocket.service';

interface FolderConnectProps {
  onConnect: () => void
}

const WatermarkLogo = () => (
  <svg
    width="300"
    height="300"
    viewBox="0 0 512 512"
    className="absolute inset-0 m-auto opacity-[0.015]"
    style={{ zIndex: 0 }}
  >
    <defs>
      <linearGradient
        id="watermark-grad1"
        x1="265.13162"
        y1="152.08855"
        x2="456.58057"
        y2="295.04551"
        gradientUnits="userSpaceOnUse"
      >
        <stop style={{ stopColor: "#ffffff", stopOpacity: 1 }} offset="0" />
        <stop style={{ stopColor: "#ffffff", stopOpacity: 0 }} offset="1" />
      </linearGradient>
      <linearGradient
        id="watermark-grad2"
        x1="59.827798"
        y1="254.1107"
        x2="185.78105"
        y2="104.22633"
        gradientUnits="userSpaceOnUse"
      >
        <stop style={{ stopColor: "#ffffff", stopOpacity: 1 }} offset="0" />
        <stop style={{ stopColor: "#ffffff", stopOpacity: 0 }} offset="1" />
      </linearGradient>
      <linearGradient
        id="watermark-grad3"
        x1="143.58672"
        y1="213.17589"
        x2="227.9754"
        y2="213.17589"
        gradientUnits="userSpaceOnUse"
      >
        <stop style={{ stopColor: "#ffffff", stopOpacity: 1 }} offset="0" />
        <stop style={{ stopColor: "#ffffff", stopOpacity: 0 }} offset="1" />
      </linearGradient>
      <linearGradient
        id="watermark-grad4"
        x1="59.198033"
        y1="130.67651"
        x2="164.36899"
        y2="130.67651"
        gradientUnits="userSpaceOnUse"
      >
        <stop style={{ stopColor: "#ffffff", stopOpacity: 1 }} offset="0" />
        <stop style={{ stopColor: "#ffffff", stopOpacity: 0 }} offset="1" />
      </linearGradient>
      <linearGradient
        id="watermark-grad5"
        x1="227.9754"
        y1="236.79212"
        x2="371.56212"
        y2="236.79212"
        gradientUnits="userSpaceOnUse"
      >
        <stop style={{ stopColor: "#f9f9f9", stopOpacity: 1 }} offset="0" />
        <stop style={{ stopColor: "#f9f9f9", stopOpacity: 0 }} offset="1" />
      </linearGradient>
      <linearGradient
        id="watermark-grad6"
        x1="369.67282"
        y1="206.56335"
        x2="455.9508"
        y2="206.56335"
        gradientUnits="userSpaceOnUse"
      >
        <stop style={{ stopColor: "#ffffff", stopOpacity: 1 }} offset="0" />
        <stop style={{ stopColor: "#ffffff", stopOpacity: 0 }} offset="1" />
      </linearGradient>
    </defs>

    <path
      style={{ fill: "url(#watermark-grad2)", fillOpacity: 1 }}
      d="M 204.67405,379.74908 227.34563,294.73063 144.21648,151.14391 59.827798,128.47232 Z"
    />
    <path
      style={{ fill: "url(#watermark-grad1)", fillOpacity: 1 }}
      d="m 226.77254,295.04551 143.94569,-84.0738 85.86234,22.92922 -252.53629,145.21838 z"
    />
    <path
      style={{ fill: "url(#watermark-grad3)", fillOpacity: 1 }}
      d="M 227.9754,296.61992 V 253.92763 L 165.46527,129.73186 143.58672,151.07801 Z"
    />
    <path
      style={{ fill: "url(#watermark-grad4)", fillOpacity: 1 }}
      d="M 59.198033,128.4045 142.6974,151.77368 164.36899,131.00107 78.320028,109.57934 Z"
    />
    <path style={{ fill: "#333333", fillOpacity: 1 }} d="m 227.34563,295.36039 12.59533,-40.30504" />
    <path
      style={{ fill: "url(#watermark-grad5)", fillOpacity: 1 }}
      d="m 370.30258,179.48339 1.25954,31.48832 -143.58672,83.12915 0.62977,-39.04551 z"
    />
    <path
      style={{ fill: "url(#watermark-grad6)", fillOpacity: 1 }}
      d="m 369.67282,179.48339 86.27798,24.56089 -0.62977,29.59902 -83.75891,-22.67159 z"
    />
  </svg>
)

const MainLogo = () => (
  <svg width="80" height="80" viewBox="0 0 512 512" className="mx-auto mb-6">
    <defs>
      <linearGradient
        id="main-grad1"
        x1="265.13162"
        y1="152.08855"
        x2="456.58057"
        y2="295.04551"
        gradientUnits="userSpaceOnUse"
      >
        <stop style={{ stopColor: "#ffffff", stopOpacity: 1 }} offset="0" />
        <stop style={{ stopColor: "#ffffff", stopOpacity: 0 }} offset="1" />
      </linearGradient>
      <linearGradient
        id="main-grad2"
        x1="59.827798"
        y1="254.1107"
        x2="185.78105"
        y2="104.22633"
        gradientUnits="userSpaceOnUse"
      >
        <stop style={{ stopColor: "#ffffff", stopOpacity: 1 }} offset="0" />
        <stop style={{ stopColor: "#ffffff", stopOpacity: 0 }} offset="1" />
      </linearGradient>
      <linearGradient
        id="main-grad3"
        x1="143.58672"
        y1="213.17589"
        x2="227.9754"
        y2="213.17589"
        gradientUnits="userSpaceOnUse"
      >
        <stop style={{ stopColor: "#ffffff", stopOpacity: 1 }} offset="0" />
        <stop style={{ stopColor: "#ffffff", stopOpacity: 0 }} offset="1" />
      </linearGradient>
      <linearGradient
        id="main-grad4"
        x1="59.198033"
        y1="130.67651"
        x2="164.36899"
        y2="130.67651"
        gradientUnits="userSpaceOnUse"
      >
        <stop style={{ stopColor: "#ffffff", stopOpacity: 1 }} offset="0" />
        <stop style={{ stopColor: "#ffffff", stopOpacity: 0 }} offset="1" />
      </linearGradient>
      <linearGradient
        id="main-grad5"
        x1="227.9754"
        y1="236.79212"
        x2="371.56212"
        y2="236.79212"
        gradientUnits="userSpaceOnUse"
      >
        <stop style={{ stopColor: "#f9f9f9", stopOpacity: 1 }} offset="0" />
        <stop style={{ stopColor: "#f9f9f9", stopOpacity: 0 }} offset="1" />
      </linearGradient>
      <linearGradient
        id="main-grad6"
        x1="369.67282"
        y1="206.56335"
        x2="455.9508"
        y2="206.56335"
        gradientUnits="userSpaceOnUse"
      >
        <stop style={{ stopColor: "#ffffff", stopOpacity: 1 }} offset="0" />
        <stop style={{ stopColor: "#ffffff", stopOpacity: 0 }} offset="1" />
      </linearGradient>
    </defs>

    <path
      style={{ fill: "url(#main-grad2)", fillOpacity: 1 }}
      d="M 204.67405,379.74908 227.34563,294.73063 144.21648,151.14391 59.827798,128.47232 Z"
    />
    <path
      style={{ fill: "url(#main-grad1)", fillOpacity: 1 }}
      d="m 226.77254,295.04551 143.94569,-84.0738 85.86234,22.92922 -252.53629,145.21838 z"
    />
    <path
      style={{ fill: "url(#main-grad3)", fillOpacity: 1 }}
      d="M 227.9754,296.61992 V 253.92763 L 165.46527,129.73186 143.58672,151.07801 Z"
    />
    <path
      style={{ fill: "url(#main-grad4)", fillOpacity: 1 }}
      d="M 59.198033,128.4045 142.6974,151.77368 164.36899,131.00107 78.320028,109.57934 Z"
    />
    <path style={{ fill: "#333333", fillOpacity: 1 }} d="m 227.34563,295.36039 12.59533,-40.30504" />
    <path
      style={{ fill: "url(#main-grad5)", fillOpacity: 1 }}
      d="m 370.30258,179.48339 1.25954,31.48832 -143.58672,83.12915 0.62977,-39.04551 z"
    />
    <path
      style={{ fill: "url(#main-grad6)", fillOpacity: 1 }}
      d="m 369.67282,179.48339 86.27798,24.56089 -0.62977,29.59902 -83.75891,-22.67159 z"
    />
  </svg>
)

interface FileItem {
    name: string;
    path: string;
    isDirectory: boolean;
  }
  
  export default function FolderConnect({ onConnect }: FolderConnectProps) {
    const [isConnecting, setIsConnecting] = useState(false);
    const [discoveryMessages, setDiscoveryMessages] = useState<string[]>([]);
    const [isDiscovering, setIsDiscovering] = useState(false);
  
    const handleOpenFolder = async () => {
      setIsConnecting(true);
      setIsDiscovering(true);
      setDiscoveryMessages([]);
  
      try {
        // @ts-ignore - showDirectoryPicker is not in TypeScript types yet
        const dirHandle = await window.showDirectoryPicker();
        
        // Simulate file discovery
        await new Promise((resolve) => setTimeout(resolve, 1500));
        
        // Add some sample file discovery messages
        const sampleFiles = ['data1.xlsx', 'reports.xlsx', 'analysis.xlsx'];
        for (const file of sampleFiles) {
          setDiscoveryMessages(prev => [...prev, `Found file: ${file}`]);
          await new Promise(resolve => setTimeout(resolve, 300));
        }
        
        // Complete the process
        setIsConnecting(false);
        setIsDiscovering(false);
        onConnect();
      } catch (err) {
        console.log("User cancelled folder selection");
        setIsConnecting(false);
        setIsDiscovering(false);
      }
    };
  
    return (
      <div
        className={`flex flex-col items-center justify-center min-h-screen text-white relative overflow-hidden`}
        style={{ backgroundColor: "#0a0a0a" }}
      >
        {/* Background elements */}
        <div
          className="absolute inset-0 pointer-events-none"
          style={{
            background: `radial-gradient(circle at center, rgba(20, 20, 20, 0.3) 0%, rgba(10, 10, 10, 0.8) 40%, rgba(10, 10, 10, 1) 70%)`,
            zIndex: 1,
          }}
        />
        <WatermarkLogo />
  
        {/* Main content */}
        <div className="relative z-10 text-center space-y-8 animate-fade-in">
          {/* Logo and Title */}
          <div className="space-y-4">
            <MainLogo />
            <div className="space-y-1">
              <h1 className="text-5xl font-bold text-gray-100 tracking-wide">Volute</h1>
              <h2 className="text-xl font-light text-gray-300">Workspaces</h2>
            </div>
          </div>
  
          <div className="flex justify-center">
            <button
              onClick={handleOpenFolder}
              disabled={isConnecting}
              className="flex items-center gap-2 px-5 py-2.5 rounded-3xl text-sm font-medium transition-all duration-200 hover:scale-105 hover:shadow-lg disabled:opacity-50 disabled:cursor-not-allowed"
              style={{
                background: "linear-gradient(135deg, #2a2a2a 0%, #1a1a1a 100%)",
                border: "1px solid #333333",
                color: "#e5e5e5",
              }}
            >
              {isConnecting ? (
                <>
                  <div className="w-4 h-4 border-2 border-gray-400 border-t-transparent rounded-full animate-spin" />
                  Opening Workspace...
                </>
              ) : (
                <>
                  <FolderOpen size={16} />
                  Open Folder
                </>
              )}
            </button>
          </div>
  
          {/* Instructions */}
          <div className="max-w-md mx-auto text-center">
            <p className="text-sm text-gray-500 leading-relaxed">
              Select a folder to open your workspace. The AI assistant will have full context of your project files.
            </p>
          </div>
        </div>
  
        {/* File discovery progress */}
        <FileDiscoveryProgress 
          messages={discoveryMessages} 
          isActive={isDiscovering || discoveryMessages.length > 0} 
        />
      </div>
    );
  }