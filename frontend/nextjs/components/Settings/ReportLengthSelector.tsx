import React, { ChangeEvent } from 'react';
import { REPORT_LENGTH_OPTIONS } from '@/config/researchSettings';

interface ReportLengthSelectorProps {
  totalWords: number;
  onTotalWordsChange: (event: ChangeEvent<HTMLSelectElement>) => void;
}

export default function ReportLengthSelector({
  totalWords,
  onTotalWordsChange,
}: ReportLengthSelectorProps) {
  const safeValue = REPORT_LENGTH_OPTIONS.some((option) => option.value === totalWords)
    ? totalWords
    : REPORT_LENGTH_OPTIONS[1].value;

  return (
    <div className="form-group">
      <label htmlFor="total_words" className="agent_question">
        Report Length{' '}
      </label>
      <select
        name="total_words"
        id="total_words"
        value={safeValue}
        onChange={onTotalWordsChange}
        className="form-control-static"
        required
      >
        {REPORT_LENGTH_OPTIONS.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    </div>
  );
}
