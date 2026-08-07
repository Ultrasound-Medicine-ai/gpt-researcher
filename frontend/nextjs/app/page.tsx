"use client";

import { useRef, useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useWebSocket } from '@/hooks/useWebSocket';
import { useResearchHistoryContext } from '@/hooks/ResearchHistoryContext';
import { startLanggraphResearch } from '../components/Langgraph/Langgraph';
import findDifferences from '../helpers/findDifferences';
import { Data, ChatBoxSettings, QuestionData, ChatMessage, ChatData } from '../types/data';
import { preprocessOrderedData } from '../utils/dataProcessing';
import { toast } from "react-hot-toast";
import { v4 as uuidv4 } from 'uuid';

import Hero from "@/components/Hero";
import CopilotResearchContent from "@/components/research/CopilotResearchContent";
import HumanFeedback from "@/components/HumanFeedback";
import ResearchSidebar from "@/components/ResearchSidebar";
import { getAppropriateLayout } from "@/utils/getLayout";
import {
  buildCombinedResearchContext,
  buildConversationMessages,
  buildResearchTask,
} from '@/utils/buildChatContext';
import { DEFAULT_CHAT_BOX_SETTINGS, readChatBoxSettingsFromStorage } from "@/config/researchSettings";

export default function Home() {
  const router = useRouter();
  const [promptValue, setPromptValue] = useState("");
  const [chatPromptValue, setChatPromptValue] = useState("");
  const [showResult, setShowResult] = useState(false);
  const [answer, setAnswer] = useState("");
  const [loading, setLoading] = useState(false);
  const [isInChatMode, setIsInChatMode] = useState(false);
  const [chatBoxSettings, setChatBoxSettings] = useState<ChatBoxSettings>(DEFAULT_CHAT_BOX_SETTINGS);
  const [question, setQuestion] = useState("");
  const [orderedData, setOrderedData] = useState<Data[]>([]);
  const [showHumanFeedback, setShowHumanFeedback] = useState(false);
  const [questionForHuman, setQuestionForHuman] = useState<true | false>(false);
  const [allLogs, setAllLogs] = useState<any[]>([]);
  const [isStopped, setIsStopped] = useState(false);
  const mainContentRef = useRef<HTMLDivElement>(null);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [currentResearchId, setCurrentResearchId] = useState<string | null>(null);
  const [isProcessingChat, setIsProcessingChat] = useState(false);
  const [sessionMode, setSessionMode] = useState<'research' | 'chat' | null>(null);
  const [homeInputMode, setHomeInputMode] = useState<'research' | 'chat'>('research');
  const settingsHydratedRef = useRef(false);

  useEffect(() => {
    setChatBoxSettings(readChatBoxSettingsFromStorage());
    settingsHydratedRef.current = true;
  }, []);

  const {
    history, 
    saveResearch, 
    updateResearch,
    getResearchById, 
    deleteResearch,
    addChatMessage,
    getChatMessages
  } = useResearchHistoryContext();

  // Only initialize the WebSocket hook reference, don't connect automatically
  const websocketRef = useRef(useWebSocket(
    setOrderedData,
    setAnswer,
    setLoading,
    setShowHumanFeedback,
    setQuestionForHuman
  ));
  
  // Use the reference to access websocket functions
  const { socket, initializeWebSocket } = websocketRef.current;

  const handleFeedbackSubmit = (feedback: string | null) => {
    if (socket) {
      socket.send(JSON.stringify({ type: 'human_feedback', content: feedback }));
    }
    setShowHumanFeedback(false);
  };

  const extractChatMessagesFromOrderedData = (data: Data[]) => {
    return buildConversationMessages(data, question.trim());
  };

  const handleStartChat = async (message: string) => {
    const trimmed = message.trim();
    if (!trimmed) return;
    setSessionMode('chat');
    setIsInChatMode(true);
    setShowResult(true);
    setAnswer('');
    setQuestion(trimmed);
    setCurrentResearchId(null);
    setOrderedData([]);
    setLoading(false);
    await handleChat(trimmed);
  };

  const handleChat = async (message: string) => {
    setIsInChatMode(true);
    setShowResult(true);
    setIsProcessingChat(true);
    setChatPromptValue("");
    
    const userMessage: ChatMessage = {
      role: 'user',
      content: message,
      timestamp: Date.now()
    };
    
    const questionData: QuestionData = { type: 'question', content: message };
    let researchId = currentResearchId;

    if (!researchId) {
      try {
        researchId = await saveResearch(message, '', [questionData]);
        setCurrentResearchId(researchId);
      } catch (error) {
        console.error('Error creating chat session:', error);
      }
    } else {
      addChatMessage(researchId, userMessage).catch(error => {
        console.error('Error adding chat message to history:', error);
      });
    }

    setOrderedData(prevOrder => [...prevOrder, questionData]);
    
    // Desktop: call chat API
    try {
      const formattedMessages = buildConversationMessages(
        orderedData,
        question.trim(),
        userMessage
      );
      
      // Call the chat API
      const response = await fetch(`/api/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          report: answer || "",
          messages: formattedMessages,
          research_topic: question.trim() || message,
          research_context: buildCombinedResearchContext(orderedData, question.trim()),
          report_language: chatBoxSettings.report_language || 'chinese',
        }),
      });
      
      if (!response.ok) {
        throw new Error(`Failed to get chat response: ${response.status}`);
      }
      
      const data = await response.json();
      
      if (data.response) {
        // Check if response contains valid content
        if (!data.response.content) {
          console.error('Response content is null or empty');
          // Show error message in results
          setOrderedData(prevOrder => [...prevOrder, { 
            type: 'chat', 
            content: 'I apologize, but I couldn\'t generate a proper response. Please try asking your question again.' 
          }]);
        } else {
          if (researchId) {
            addChatMessage(researchId, data.response).catch(console.error);
          }
          
          setOrderedData(prevOrder => {
            return [...prevOrder, { 
              type: 'chat', 
              content: data.response.content,
              metadata: data.response.metadata
            }];
          });

          const chatData: ChatData = {
            type: 'chat',
            content: data.response.content,
            metadata: data.response.metadata,
          };
          const updatedOrderedData = [...orderedData, questionData, chatData];
          if (researchId) {
            updateResearch(researchId, answer || '', updatedOrderedData).catch(console.error);
          }
        }
        
        if (!isInChatMode) {
          setIsInChatMode(true);
        }
      } else {
        // Show error message
        setOrderedData(prevOrder => [...prevOrder, { 
          type: 'chat', 
          content: 'Sorry, something went wrong. Please try again.' 
        }]);
      }
    } catch (error) {
      console.error('Error during chat:', error);
      
      // Add error message to display
      setOrderedData(prevOrder => [...prevOrder, { 
        type: 'chat', 
        content: 'Sorry, there was an error processing your request. Please try again.' 
      }]);
    } finally {
      setIsProcessingChat(false);
    }
  };

  const handleDisplayResult = async (newQuestion: string) => {
    setSessionMode('research');
    setIsInChatMode(true);
    setShowResult(true);
    setLoading(false);
    setQuestion(newQuestion);
    setPromptValue("");
    setAnswer("");
    setCurrentResearchId(null);
    setOrderedData([{ type: 'question', content: newQuestion }]);

    try {
      const researchId = await saveResearch(newQuestion, '', [{ type: 'question', content: newQuestion }]);
      setCurrentResearchId(researchId);
    } catch (error) {
      console.error('Error saving research prep session:', error);
    }
  };

  const handleGenerateReport = async () => {
    const task = buildResearchTask(question, orderedData).trim();
    if (!task || loading) return;

    setLoading(true);
    setIsInChatMode(true);
    setAnswer("");

    const storedConfig = localStorage.getItem('apiVariables');
    const apiVariables = storedConfig ? JSON.parse(storedConfig) : {};
    const langgraphHostUrl = apiVariables.LANGGRAPH_HOST_URL;

    if (chatBoxSettings.report_type === 'multi_agents' && langgraphHostUrl) {
      const { streamResponse, host, thread_id } = await startLanggraphResearch(
        task,
        chatBoxSettings.report_source,
        langgraphHostUrl
      );
      const langsmithGuiLink = `https://smith.langchain.com/studio/thread/${thread_id}?baseUrl=${host}`;
      setOrderedData((prevOrder) => [...prevOrder, { type: 'langgraphButton', link: langsmithGuiLink }]);

      let previousChunk = null;
      for await (const chunk of streamResponse) {
        if (chunk.data.report != null && chunk.data.report != "Full report content here") {
          setOrderedData((prevOrder) => [...prevOrder, { ...chunk.data, output: chunk.data.report, type: 'report' }]);
          setLoading(false);
          setAnswer(chunk.data.report);
        } else if (previousChunk) {
          const differences = findDifferences(previousChunk, chunk);
          setOrderedData((prevOrder) => [...prevOrder, { type: 'differences', content: 'differences', output: JSON.stringify(differences) }]);
        }
        previousChunk = chunk;
      }
    } else {
      initializeWebSocket(task, chatBoxSettings);
    }
  };

  const reset = () => {
    setSessionMode(null);
    // Reset UI states
    setShowResult(false);
    setPromptValue("");
    setIsStopped(false);
    setIsInChatMode(false);
    setCurrentResearchId(null); // Reset research ID
    setIsProcessingChat(false);
    setChatPromptValue("");
    
    // Clear previous research data
    setQuestion("");
    setAnswer("");
    setOrderedData([]);
    setAllLogs([]);

    // Reset feedback states
    setShowHumanFeedback(false);
    setQuestionForHuman(false);
    
    // Clean up connections
    if (socket) {
      socket.close();
    }
    setLoading(false);
  };

  const handleGoHome = (mode: 'research' | 'chat' = 'research') => {
    reset();
    setHomeInputMode(mode);
    setSidebarOpen(false);
  };

  const handleStartNewChat = () => {
    handleGoHome('chat');
  };

  const handleClickSuggestion = (value: string) => {
    setPromptValue(value);
    const element = document.getElementById('input-area');
    if (element) {
      element.scrollIntoView({ behavior: 'smooth' });
    }
  };

  /**
   * Handles stopping the current research
   * - Closes WebSocket connection
   * - Stops loading state
   * - Marks research as stopped
   * - Preserves current results
   * - Reloads the page to fully reset the connection
   */
  const handleStopResearch = () => {
    if (socket) {
      socket.close();
    }
    setLoading(false);
    setIsStopped(true);
    
    // Reload the page to completely reset the socket connection
    window.location.reload();
  };

  /**
   * Handles starting a new research
   * - Clears all previous research data and states
   * - Resets UI to initial state
   * - Closes any existing WebSocket connections
   */
  const handleStartNewResearch = () => {
    handleGoHome('research');
  };

  const handleCopyUrl = () => {
    if (!currentResearchId) return;
    
    const url = `${window.location.origin}/research/${currentResearchId}`;
    navigator.clipboard.writeText(url)
      .then(() => {
        toast.success("URL copied to clipboard!");
      })
      .catch(() => {
        toast.error("Failed to copy URL");
      });
  };

  // Add a ref to track if an update is in progress to prevent infinite loops
  const isUpdatingRef = useRef(false);

  // Save or update research in history based on mode
  useEffect(() => {
    // Define an async function inside the effect
    const saveOrUpdateResearch = async () => {
      // Prevent infinite loops by checking if we're already updating
      if (isUpdatingRef.current) return;
      
      if (showResult && !loading && answer && question && orderedData.length > 0) {
        if (isInChatMode && currentResearchId) {
          // Prevent redundant updates by checking if data has changed
          try {
            const currentResearch = await getResearchById(currentResearchId);
            if (currentResearch && (currentResearch.answer !== answer || JSON.stringify(currentResearch.orderedData) !== JSON.stringify(orderedData))) {
              isUpdatingRef.current = true;
              await updateResearch(currentResearchId, answer, orderedData);
              // Reset the flag after a short delay to allow state updates to complete
              setTimeout(() => {
                isUpdatingRef.current = false;
              }, 100);
            }
          } catch (error) {
            console.error('Error updating research:', error);
            isUpdatingRef.current = false;
          }
        } else if (!isInChatMode) {
          // Check if this is a new research (not loaded from history)
          const isNewResearch = !history.some(item => 
            item.question === question && item.answer === answer
          );
          
          if (isNewResearch) {
            isUpdatingRef.current = true;
            try {
              const newId = await saveResearch(question, answer, orderedData);
              setCurrentResearchId(newId);
              
              // Don't navigate to the research page URL anymore
              // Just save the ID for sharing purposes
              
            } catch (error) {
              console.error('Error saving research:', error);
            } finally {
              // Reset the flag after a short delay to allow state updates to complete
              setTimeout(() => {
                isUpdatingRef.current = false;
              }, 100);
            }
          }
        }
      }
    };
    
    // Call the async function
    saveOrUpdateResearch();
  }, [showResult, loading, answer, question, orderedData, history, saveResearch, updateResearch, isInChatMode, currentResearchId, getResearchById]);

  // Handle selecting a research from history
  const handleSelectResearch = async (id: string) => {
    try {
      const research = await getResearchById(id);
      if (research) {
        // Navigate to the research page instead of loading it here
        router.push(`/research/${id}`);
      }
    } catch (error) {
      console.error('Error selecting research:', error);
      toast.error('Could not load the selected research');
    }
  };

  // Toggle sidebar
  const toggleSidebar = () => {
    setSidebarOpen(!sidebarOpen);
  };

  /**
   * Processes ordered data into logs for display
   * Updates whenever orderedData changes
   */
  useEffect(() => {
    const groupedData = preprocessOrderedData(orderedData);
    const statusReports = ["agent_generated", "starting_research", "planning_research", "error"];
    
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
      // Process status reports
      else if (statusReports.includes(data.content)) {
        return [...acc, {
          header: data.content,
          text: data.output,
          metadata: data.metadata,
          key: `${data.type}-${data.content}`,
        }];
      }
      return acc;
    }, []);
    
    setAllLogs(newLogs);
  }, [orderedData]);

  // Save chatBoxSettings to localStorage when they change
  useEffect(() => {
    if (!settingsHydratedRef.current) return;
    localStorage.setItem('chatBoxSettings', JSON.stringify(chatBoxSettings));
  }, [chatBoxSettings]);

  // Set chat mode when a report is complete
  useEffect(() => {
    if (showResult && !loading && answer && !isInChatMode) {
      setIsInChatMode(true);
    }
  }, [showResult, loading, answer, isInChatMode]);

  const copilotContent = (
    <CopilotResearchContent
      orderedData={orderedData}
      answer={answer}
      allLogs={allLogs}
      chatBoxSettings={chatBoxSettings}
      loading={loading}
      isStopped={isStopped}
      promptValue={promptValue}
      chatPromptValue={chatPromptValue}
      setPromptValue={setPromptValue}
      setChatPromptValue={setChatPromptValue}
      handleDisplayResult={handleDisplayResult}
      handleChat={handleChat}
      handleClickSuggestion={handleClickSuggestion}
      currentResearchId={currentResearchId || undefined}
      onShareClick={currentResearchId ? handleCopyUrl : undefined}
      reset={reset}
      isProcessingChat={isProcessingChat}
      onNewResearch={handleStartNewResearch}
      toggleSidebar={toggleSidebar}
      isInChatMode={isInChatMode}
      sessionMode={sessionMode}
      onGenerateReport={handleGenerateReport}
      onGoHome={() => handleGoHome('research')}
      onNewChat={handleStartNewChat}
    />
  );

  return (
    <>
      {!showResult ? (
        getAppropriateLayout({
          loading,
          isStopped,
          showResult,
          onStop: handleStopResearch,
          onNewResearch: handleStartNewResearch,
          chatBoxSettings,
          setChatBoxSettings,
          mainContentRef,
          toggleSidebar,
          children: (
            <>
              <ResearchSidebar
                history={history}
                onSelectResearch={handleSelectResearch}
                onNewResearch={handleStartNewResearch}
                onDeleteResearch={deleteResearch}
                isOpen={sidebarOpen}
                toggleSidebar={toggleSidebar}
              />
              <Hero
                promptValue={promptValue}
                setPromptValue={setPromptValue}
                handleDisplayResult={handleDisplayResult}
                handleStartChat={handleStartChat}
                defaultInputMode={homeInputMode}
              />
            </>
          ),
        })
      ) : (
        getAppropriateLayout({
          loading,
          isStopped,
          showResult,
          onStop: handleStopResearch,
          onNewResearch: handleStartNewResearch,
          chatBoxSettings,
          setChatBoxSettings,
          mainContentRef,
          toggleSidebar,
          children: (
            <div className="relative">
              <ResearchSidebar
                history={history}
                onSelectResearch={handleSelectResearch}
                onNewResearch={handleStartNewResearch}
                onDeleteResearch={deleteResearch}
                isOpen={sidebarOpen}
                toggleSidebar={toggleSidebar}
              />
              {copilotContent}
              {showHumanFeedback && false && (
                <HumanFeedback
                  questionForHuman={questionForHuman}
                  websocket={socket}
                  onFeedbackSubmit={handleFeedbackSubmit}
                />
              )}
            </div>
          ),
        })
      )}
    </>
  );
}