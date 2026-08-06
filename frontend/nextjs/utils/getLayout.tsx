import React from 'react';
import CopilotLayout from '@/components/layouts/CopilotLayout';
import { ChatBoxSettings } from '@/types/data';

interface LayoutProps {
  children: React.ReactNode;
  loading: boolean;
  isStopped: boolean;
  showResult: boolean;
  onStop?: () => void;
  onNewResearch?: () => void;
  chatBoxSettings: ChatBoxSettings;
  setChatBoxSettings: React.Dispatch<React.SetStateAction<ChatBoxSettings>>;
  mainContentRef?: React.RefObject<HTMLDivElement>;
  toastOptions?: Record<string, any>;
  toggleSidebar?: () => void;
}

export const getAppropriateLayout = ({
  children,
  loading,
  isStopped,
  showResult,
  onStop,
  onNewResearch,
  chatBoxSettings,
  setChatBoxSettings,
  mainContentRef,
  toastOptions = {},
  toggleSidebar,
}: LayoutProps) => (
  <CopilotLayout
    loading={loading}
    isStopped={isStopped}
    showResult={showResult}
    onStop={onStop}
    onNewResearch={onNewResearch}
    chatBoxSettings={chatBoxSettings}
    setChatBoxSettings={setChatBoxSettings}
    mainContentRef={mainContentRef}
    toastOptions={toastOptions}
    toggleSidebar={toggleSidebar}
  >
    {children}
  </CopilotLayout>
);
