"use client";

import React, { useEffect, useState, useRef } from "react";
import { useRouter } from "next/navigation";
import { loadStoredJobForSession, useResearchJob } from '@/hooks/useResearchJob';
import { useResearchHistoryContext } from "@/hooks/ResearchHistoryContext";
import { preprocessOrderedData } from "@/utils/dataProcessing";
import { ChatBoxSettings, Data, ChatData, ChatMessage, QuestionData } from "@/types/data";
import { toast } from "react-hot-toast";
import { getAppropriateLayout } from "@/utils/getLayout";
import { DEFAULT_CHAT_BOX_SETTINGS, readChatBoxSettingsFromStorage } from "@/config/researchSettings";
import { buildCombinedResearchContext, buildConversationMessages } from "@/utils/buildChatContext";

import ResearchPageLayout from "@/components/layouts/ResearchPageLayout";
import CopilotLayout from "@/components/layouts/CopilotLayout";
import CopilotResearchContent from "@/components/research/CopilotResearchContent";
import NotFoundContent from "@/components/research/NotFoundContent";
import LoadingDots from "@/components/LoadingDots";
import ResearchSidebar from "@/components/ResearchSidebar";
import { apiFetch } from '@/lib/apiFetch';
import {
  chatReportCreatedMessage,
  mergeChatWithReportTopic,
  submitChatReportJob,
} from '@/lib/submitChatReport';

export default function ResearchPage({ params }: { params: { id: string } }) {
  const router = useRouter();
  const { id } = params;
  const [loading, setLoading] = useState(true);
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState("");
  const [chatPromptValue, setChatPromptValue] = useState("");
  const [orderedData, setOrderedData] = useState<Data[]>([]);
  const [allLogs, setAllLogs] = useState<any[]>([]);
  const [isStopped, setIsStopped] = useState(false);
  const [, setShowHumanFeedback] = useState(false);
  const [, setQuestionForHuman] = useState<true | false>(false);
  const [currentResearchId, setCurrentResearchId] = useState<string | null>(null);
  const [isProcessingChat, setIsProcessingChat] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [chatBoxSettings, setChatBoxSettings] = useState<ChatBoxSettings>(DEFAULT_CHAT_BOX_SETTINGS);
  const [notFound, setNotFound] = useState(false);
  const [fetchAttempted, setFetchAttempted] = useState(false);
  const settingsHydratedRef = useRef(false);
  const bottomRef = useRef<HTMLDivElement>(null);
  const toastShownRef = useRef(false);

  const { 
    history,
    getResearchById, 
    addChatMessage,
    getChatMessages,
    updateResearch,
    deleteResearch,
    saveResearch,
  } = useResearchHistoryContext();

  const sideReportSessionIdRef = useRef<string | null>(null);

  // Resume this page's job; chat may also attach a newer side-report job. :-)
  const { observeJob } = useResearchJob(
    setOrderedData,
    setAnswer,
    setLoading,
    () => setShowHumanFeedback(false),
    () => setQuestionForHuman(false),
    undefined,
    id,
  );

  // Toggle sidebar
  const toggleSidebar = () => {
    setSidebarOpen(!sidebarOpen);
  };

  // Handle selecting a research from the sidebar
  const handleSelectResearch = async (researchId: string) => {
    if (researchId !== id) {
      router.push(`/research/${researchId}`);
    }
    setSidebarOpen(false);
  };

  // Save chatBoxSettings to localStorage when they change
  useEffect(() => {
    if (!settingsHydratedRef.current) return;
    localStorage.setItem('chatBoxSettings', JSON.stringify(chatBoxSettings));
  }, [chatBoxSettings]);

  useEffect(() => {
    setChatBoxSettings(readChatBoxSettingsFromStorage());
    settingsHydratedRef.current = true;
  }, []);

  // Load research data on mount
  useEffect(() => {
    // Prevent multiple fetch attempts for the same ID
    if (fetchAttempted) {
      console.log(`Skipping duplicate fetch for research ${id} (already attempted)`);
      return;
    }
    
    const fetchResearch = async () => {
      setLoading(true);
      setFetchAttempted(true); // Mark that we've attempted a fetch
      console.log(`Attempting to load research ${id}...`);
      
      // Reset toast tracking on each fetch attempt
      toastShownRef.current = false;
      
      // Step 1: Try to find it in localStorage first
      const storedHistory = localStorage.getItem('researchHistory');
      let localItem = null;
      
      if (storedHistory) {
        try {
          const localHistory = JSON.parse(storedHistory);
          localItem = localHistory.find((item: any) => item.id === id);
          
          if (localItem) {
            console.log(`Found research ${id} in localStorage!`);
            console.log(`- Question length: ${localItem.question.length}`);
            console.log(`- Answer length: ${localItem.answer?.length || 0}`);
          }
        } catch (error) {
          console.error('Error parsing localStorage:', error);
        }
      }
      
      // Step 2: Try to find it in the backend
      let foundInBackend = false;
      try {
        console.log(`Checking backend for research ${id}...`);
        const response = await apiFetch(`/api/reports/${id}`);
        
        if (response.ok) {
          console.log(`Found research ${id} in backend!`);
          foundInBackend = true;
          const data = await response.json();
          
          // Validate backend data
          if (!data.report) {
            console.error(`Backend response missing report object for ${id}`);
          } else {
            console.log(`- Question length: ${data.report.question.length}`);
            console.log(`- Answer length: ${data.report.answer?.length || 0}`);
            
            // Use the backend data, ensuring orderedData and chatMessages are arrays
            setQuestion(data.report.question);
            setAnswer(data.report.answer || '');
            const incoming = Array.isArray(data.report.orderedData)
              ? data.report.orderedData
              : [];
            // Don't wipe live poll lines if Job resume already started. :-)
            setOrderedData((prev) => {
              if (!loadStoredJobForSession(id)?.jobId) return incoming;
              const live = prev.filter((item) =>
                ['job_live_status', 'job_status', 'job_resume'].includes(
                  String((item as { content?: string }).content || '')
                )
              );
              return [...incoming.filter((item) => (item as { content?: string }).content !== 'job_live_status'), ...live];
            });
            setCurrentResearchId(id);
            setLoading(!loadStoredJobForSession(id)?.jobId);
          }
        } else if (response.status === 500) {
          // Handle server error
          console.error(`Backend server error when fetching research ${id}`);
          
          // Only show error toast if we haven't shown a toast yet in this component instance
          if (!toastShownRef.current) {
            console.log('Showing backend error toast');
            toast.error("Server connection error. Using local data if available.", {
              id: `server-error-${id}`, // Unique ID per research
            });
            toastShownRef.current = true;
          }
          
          // If we have local data, use it even if backend fails
          if (localItem) {
            setQuestion(localItem.question);
            setAnswer(localItem.answer || '');
            setOrderedData(Array.isArray(localItem.orderedData) ? localItem.orderedData : []);
            setCurrentResearchId(id);
            setLoading(!loadStoredJobForSession(id)?.jobId);
            return;
          }
          
          // If no local data, show not found
          setNotFound(true);
          setLoading(false);
        } else {
          console.log(`Research ${id} not found in backend (status: ${response.status})`);
        }
      } catch (error) {
        console.error('Error fetching from backend:', error);
        
        // Only show error toast if we haven't shown a toast yet in this component instance
        if (!toastShownRef.current) {
          console.log('Showing fetch error toast');
          toast.error("Failed to connect to server. Using local data if available.", {
            id: `fetch-error-${id}`, // Unique ID per research
          });
          toastShownRef.current = true;
        }
        
        // If we have local data, use it as fallback
        if (localItem) {
          setQuestion(localItem.question);
          setAnswer(localItem.answer || '');
          setOrderedData(Array.isArray(localItem.orderedData) ? localItem.orderedData : []);
          setCurrentResearchId(id);
          setLoading(!loadStoredJobForSession(id)?.jobId);
          return;
        }
      }
      
      // Step 3: If found in localStorage but not in backend, save it
      if (localItem && !foundInBackend) {
        console.log(`Saving research ${id} from localStorage to backend...`);
        try {
          // Ensure data is clean and serializable
          const cleanItem = {
            id: localItem.id,
            question: localItem.question,
            answer: localItem.answer || '',
            orderedData: Array.isArray(localItem.orderedData) ? JSON.parse(JSON.stringify(localItem.orderedData)) : [],
            chatMessages: Array.isArray(localItem.chatMessages) ? JSON.parse(JSON.stringify(localItem.chatMessages)) : [],
          };
          
          const saveResponse = await apiFetch('/api/reports', {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
            },
            body: JSON.stringify(cleanItem),
          });
          
          if (saveResponse.ok) {
            console.log(`Successfully saved research ${id} to backend!`);
          } else {
            console.warn(`Failed to save research to backend: ${await saveResponse.text()}`);
          }
          
          // Use the localStorage data
          setQuestion(localItem.question);
          setAnswer(localItem.answer || '');
          setOrderedData(Array.isArray(localItem.orderedData) ? localItem.orderedData : []);
          setCurrentResearchId(id);
          setLoading(!loadStoredJobForSession(id)?.jobId);
        } catch (error) {
          console.error('Error saving to backend:', error);
          
          // Still use the localStorage data even if save fails
          setQuestion(localItem.question);
          setAnswer(localItem.answer || '');
          setOrderedData(Array.isArray(localItem.orderedData) ? localItem.orderedData : []);
          setCurrentResearchId(id);
          setLoading(!loadStoredJobForSession(id)?.jobId);
        }
      }
      
      // Step 4: If not found anywhere, show not found message
      if (!localItem && !foundInBackend) {
        console.log(`Research ${id} not found anywhere`);
        setNotFound(true);
        setLoading(false);
      }
    };
    
    fetchResearch();
  }, [id, fetchAttempted]);

  // Process ordered data into logs for display
  useEffect(() => {
    const groupedData = preprocessOrderedData(orderedData);
    const statusReports = [
      'agent_generated',
      'starting_research',
      'planning_research',
      'error',
      'job_queued',
      'job_status',
      'job_live_status',
      'job_pending_dispatch',
      'job_rate_limited',
      'job_cancelling',
      'job_resume',
      'report_trust',
    ];
    
    const newLogs = groupedData.reduce((acc: any[], data) => {
      // Process accordion blocks (grouped data)
      if (data.type === 'accordionBlock') {
        const logs = data.items.map((item: any, subIndex: any) => ({
          header: item.content,
          text: item.output,
          metadata: item.metadata,
          key: `${item.type}-${item.content}-${subIndex}`,
        }));
        return [...acc, ...logs];
      } 
      // Process status reports (legacy WS + async Job poll)
      else if (data.type === 'logs' || statusReports.includes(data.content)) {
        return [...acc, {
          header: data.content || 'status',
          text: data.output,
          metadata: data.metadata,
          key: `${data.type}-${data.content}-${acc.length}`,
        }];
      }
      return acc;
    }, []);
    
    setAllLogs(newLogs);
  }, [orderedData]);

  // Scroll to bottom when chat updates
  const scrollToBottom = () => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    // Scroll to bottom when orderedData changes
    if (isProcessingChat === false && orderedData.length > 0) {
      setTimeout(scrollToBottom, 100); // Small delay to ensure content is rendered
    }
  }, [orderedData, isProcessingChat]);

  const submitReportRequestedInChat = async (toolCall: any) =>
    submitChatReportJob({
      toolCall,
      chatBoxSettings,
      saveResearch,
      parentChatId: currentResearchId || id,
    });

  const handleChat = async (message: string) => {
    if (!currentResearchId) return;
    
    setIsProcessingChat(true);
    setChatPromptValue("");
    
    // Create a user message
    const userMessage: ChatMessage = {
      role: 'user',
      content: message,
      timestamp: Date.now()
    };
    
    // Create question data object to be shown immediately
    const questionData: QuestionData = { type: 'question', content: message };
    
    // IMPORTANT CHANGE: Add user question to UI immediately for better responsiveness
    setOrderedData(prevOrder => [...prevOrder, questionData]);
    
    // Then add to history asynchronously
    addChatMessage(currentResearchId, userMessage).catch(error => {
      console.error('Error adding chat message to history:', error);
    });
    
    try {
      const formattedMessages = buildConversationMessages(
        orderedData,
        question.trim(),
        userMessage
      );
      
      // Call the chat API
      const response = await apiFetch(`/api/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          report: answer || "",
          messages: formattedMessages,
          research_topic: question.trim() || message,
          research_context: buildCombinedResearchContext(orderedData, question.trim()),
          report_language: chatBoxSettings.report_language || 'chinese',
          session_id: currentResearchId,
          research_id: currentResearchId,
        }),
      });
      
      if (!response.ok) {
        throw new Error(`Failed to get chat response: ${response.status}`);
      }
      
      const data = await response.json();
      
      if (data.response) {
        const reportToolCall = data.response.metadata?.tool_calls?.find(
          (tool: any) => tool.tool === 'create_research_report'
            && tool.action === 'create_report'
            && typeof tool.task === 'string'
            && tool.task.trim().length > 0
        );
        if (reportToolCall) {
          try {
            const created = await submitReportRequestedInChat(reportToolCall);
            const taskText = String(reportToolCall.task || created.task || '');
            data.response.content = chatReportCreatedMessage(taskText);
            data.response.metadata = {
              ...(data.response.metadata || {}),
              report_request: {
                research_id: created.sessionId,
                job_id: created.jobId,
                task: taskText,
              },
            };
            const chatData: ChatData = {
              type: 'chat',
              content: data.response.content,
              metadata: data.response.metadata,
            };
            // Stay on this conversation: right chat unchanged, left follows new job. :-)
            sideReportSessionIdRef.current = created.sessionId;
            setAnswer('');
            setOrderedData((prev) => {
              const withUser = prev.some(
                (d) => d.type === 'question' && d.content === questionData.content
              )
                ? prev
                : [...prev, questionData];
              return [...mergeChatWithReportTopic(withUser, taskText), chatData];
            });
            addChatMessage(currentResearchId, data.response).catch(console.error);
            updateResearch(
              currentResearchId,
              answer,
              [...mergeChatWithReportTopic([...orderedData, questionData], taskText), chatData]
            ).catch(console.error);
            observeJob(created.jobId, {
              reportSessionId: created.sessionId,
              tenantId: created.tenantId,
            });
            toast.success(`左侧已开始生成：${taskText.slice(0, 28)}`);
            return;
          } catch (submitError: any) {
            console.error('Failed to submit report requested in chat:', submitError);
            data.response.content = `报告任务未能提交：${submitError?.message || '请稍后重试'}`;
            toast.error('报告任务提交失败');
          }
        }
        // Add AI response to chat history asynchronously
        addChatMessage(currentResearchId, data.response).catch(error => {
          console.error('Error adding AI response to history:', error);
        });
        
        // Add response to the UI with any metadata
        const chatData: ChatData = { 
          type: 'chat', 
          content: data.response.content,
          metadata: data.response.metadata // Include metadata from the response
        };
        setOrderedData(prevOrder => [...prevOrder, chatData]);
        
        // Update research in history with both question and response asynchronously
        // Create a copy of the current orderedData plus the new items
        const updatedOrderedData = [...orderedData, questionData, chatData];
        updateResearch(currentResearchId, answer, updatedOrderedData).catch(error => {
          console.error('Error updating research:', error);
        });
      } else {
        // Show error message
        const errorChatData: ChatData = { 
          type: 'chat', 
          content: 'Sorry, something went wrong. Please try again.' 
        };
        setOrderedData(prevOrder => [...prevOrder, errorChatData]);
      }
    } catch (error) {
      console.error('Error during chat:', error);
      
      // Add error message
      const errorChatData: ChatData = { 
        type: 'chat', 
        content: 'Sorry, there was an error processing your request. Please try again.' 
      };
      setOrderedData(prevOrder => [...prevOrder, errorChatData]);
    } finally {
      setIsProcessingChat(false);
    }
  };

  const handleNewResearch = () => {
    router.push('/');
  };

  const handleCopyUrl = () => {
    const url = window.location.href;
    navigator.clipboard.writeText(url)
      .then(() => {
        toast.success("URL copied to clipboard!", {
          id: `copy-success-${id}`, // Unique ID per research
        });
      })
      .catch(() => {
        toast.error("Failed to copy URL", {
          id: `copy-error-${id}`, // Unique ID per research
        });
      });
  };

  // Custom toast options for this page
  const toastOptions = {
    duration: 4000,
    id: 'research-page-toast',
    style: {
      background: '#363636',
      color: '#fff',
    }
  };

  if (loading) {
    return getAppropriateLayout({
      loading,
      isStopped,
      showResult: true,
      onNewResearch: handleNewResearch,
      chatBoxSettings,
      setChatBoxSettings,
      toastOptions,
      children: (
        <div className="min-h-[100vh] pt-[120px] flex items-center justify-center">
          <LoadingDots />
        </div>
      )
    });
  }

  if (notFound) {
    return getAppropriateLayout({
      loading: false,
      isStopped: false,
      showResult: false,
      onNewResearch: handleNewResearch,
      chatBoxSettings,
      setChatBoxSettings,
      toastOptions,
      children: <NotFoundContent onNewResearch={handleNewResearch} />
    });
  }

  return getAppropriateLayout({
    loading,
    isStopped,
    showResult: true,
    onNewResearch: handleNewResearch,
    chatBoxSettings,
    setChatBoxSettings,
    toastOptions,
    children: (
      <div className="relative">
        <ResearchSidebar
          history={history}
          onSelectResearch={handleSelectResearch}
          onNewResearch={handleNewResearch}
          onDeleteResearch={deleteResearch}
          isOpen={sidebarOpen}
          toggleSidebar={toggleSidebar}
        />
        <CopilotResearchContent
          orderedData={orderedData}
          answer={answer}
          allLogs={allLogs}
          chatBoxSettings={chatBoxSettings}
          loading={loading}
          isStopped={isStopped}
          promptValue=""
          chatPromptValue={chatPromptValue}
          setPromptValue={() => {}}
          setChatPromptValue={setChatPromptValue}
          handleDisplayResult={() => {}}
          handleChat={handleChat}
          handleClickSuggestion={() => {}}
          currentResearchId={currentResearchId || undefined}
          onShareClick={handleCopyUrl}
          isProcessingChat={isProcessingChat}
          onNewResearch={handleNewResearch}
          toggleSidebar={toggleSidebar}
          isInChatMode={true}
          sessionMode={
            answer || loading || Boolean(sideReportSessionIdRef.current)
              ? 'research'
              : null
          }
        />
      </div>
    )
  });
}
