import React from 'react';
import Question from './ResearchBlocks/Question';
import Report from './ResearchBlocks/Report';
import SubQuestions from './ResearchBlocks/elements/SubQuestions';
import LogsSection from './ResearchBlocks/LogsSection';
import AccessReport from './ResearchBlocks/AccessReport';
import { preprocessOrderedData } from '../utils/dataProcessing';
import { Data } from '../types/data';

interface ResearchResultsProps {
  orderedData: Data[];
  answer: string;
  allLogs: any[];
  chatBoxSettings: any;
  handleClickSuggestion: (value: string) => void;
  currentResearchId?: string;
  isProcessingChat?: boolean;
  onShareClick?: () => void;
}

export const ResearchResults: React.FC<ResearchResultsProps> = ({
  orderedData,
  answer,
  allLogs,
  chatBoxSettings,
  handleClickSuggestion,
  currentResearchId,
  isProcessingChat = false,
  onShareClick
}) => {
  const groupedData = preprocessOrderedData(orderedData);
  const pathData = groupedData.find(data => data.type === 'path');
  const initialQuestion = groupedData.find(data => data.type === 'question');

  const chatComponents = groupedData
    .filter(data => {
      if (data.type === 'question' && data === initialQuestion) {
        return false;
      }
      return (data.type === 'question' || data.type === 'chat');
    })
    .map((data, index) => {
      if (data.type === 'question') {
        return <Question key={`question-${index}`} question={data.content} />;
      } else {
        return <Report key={`chat-${index}`} answer={data.content} />;
      }
    });

  const finalReport = groupedData
    .filter(data => data.type === 'reportBlock')
    .pop();
  const subqueriesComponent = groupedData.find(data => data.content === 'subqueries');

  // Prefer post-processed answer (includes numbered references) over streamed chunks
  const reportContent =
    answer && answer.trim().length > 0
      ? answer
      : finalReport?.content || '';

  return (
    <>
      {initialQuestion && <Question question={initialQuestion.content} />}
      {orderedData.length > 0 && <LogsSection logs={allLogs} />}
      {subqueriesComponent && (
        <SubQuestions
          metadata={subqueriesComponent.metadata}
          handleClickSuggestion={handleClickSuggestion}
        />
      )}
      {reportContent && <Report answer={reportContent} researchId={currentResearchId} />}
      {pathData && <AccessReport accessData={pathData.output} report={answer} chatBoxSettings={chatBoxSettings} onShareClick={onShareClick} />}
      {chatComponents}
    </>
  );
}; 