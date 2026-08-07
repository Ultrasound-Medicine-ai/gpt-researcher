import React, { ChangeEvent } from 'react';
import { REPORT_LANGUAGE_OPTIONS } from '@/config/researchSettings';

interface ReportLanguageSelectorProps {
  reportLanguage: string;
  onReportLanguageChange: (event: ChangeEvent<HTMLSelectElement>) => void;
}

export default function ReportLanguageSelector({
  reportLanguage,
  onReportLanguageChange,
}: ReportLanguageSelectorProps) {
  const safeValue = REPORT_LANGUAGE_OPTIONS.some((option) => option.value === reportLanguage)
    ? reportLanguage
    : REPORT_LANGUAGE_OPTIONS[0].value;

  return (
    <div className="form-group">
      <label htmlFor="report_language" className="agent_question">
        Report Language{' '}
      </label>
      <select
        name="report_language"
        id="report_language"
        value={safeValue}
        onChange={onReportLanguageChange}
        className="form-control-static"
        required
      >
        {REPORT_LANGUAGE_OPTIONS.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    </div>
  );
}
