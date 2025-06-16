import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import AIChatUI from '../../components/agent-chat/agent-chat-ui';

export function AgentChatPage() {
  const navigate = useNavigate();

  useEffect(() => {
    const electron = (window as any).electron;
    if (electron?.log?.info) {
      electron.log.info('Agent Chat page loaded');
    }
  }, []);

  return (
    <div className="min-h-screen bg-[#0a0a0a]">
      <AIChatUI />
    </div>
  );
}