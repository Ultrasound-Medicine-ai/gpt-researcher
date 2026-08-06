import React, { ChangeEvent } from 'react';
import { ALLOWED_TONES } from '@/config/researchSettings';

interface ToneSelectorProps {
  tone: string;
  onToneChange: (event: ChangeEvent<HTMLSelectElement>) => void;
}

const TONE_LABELS: Record<(typeof ALLOWED_TONES)[number], string> = {
  Objective: 'Objective - Impartial presentation of facts and findings',
  Formal: 'Formal - Academic standards and structured prose',
  Analytical: 'Analytical - Critical evaluation and comparison',
};

export default function ToneSelector({ tone, onToneChange }: ToneSelectorProps) {
  const safeTone = ALLOWED_TONES.includes(tone as (typeof ALLOWED_TONES)[number])
    ? tone
    : 'Objective';

  return (
    <div className="form-group">
      <label htmlFor="tone" className="agent_question">Tone </label>
      <select
        name="tone"
        id="tone"
        value={safeTone}
        onChange={onToneChange}
        className="form-control-static"
        required
      >
        {ALLOWED_TONES.map((value) => (
          <option key={value} value={value}>
            {TONE_LABELS[value]}
          </option>
        ))}
      </select>
    </div>
  );
}
