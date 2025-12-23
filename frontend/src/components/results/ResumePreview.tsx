import React, { useState, useRef, useEffect } from 'react';
import toast from 'react-hot-toast';

interface ResumePreviewProps {
  originalResume?: string;
  tailoredResume: any;
  onTextSelect?: (text: string) => void;
  jobId?: string;
  onResumeUpdate?: (updatedResume: any) => void;
  currentATSScore?: number; // Current ATS score for comparison
}

const ResumePreview: React.FC<ResumePreviewProps> = ({
  originalResume,
  tailoredResume,
  onTextSelect,
  jobId,
  onResumeUpdate,
  currentATSScore,
}) => {
  const [viewMode, setViewMode] = useState<'original' | 'tailored' | 'compare'>('tailored');
  const [editedText, setEditedText] = useState('');
  const [hasChanges, setHasChanges] = useState(false);
  const [isCalculating, setIsCalculating] = useState(false);
  const [calculatedScore, setCalculatedScore] = useState<number | null>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const formatResume = (resume: any): string => {
    if (typeof resume === 'string') return resume;
    
    let formatted = '';
    if (resume.summary) {
      formatted += `SUMMARY\n${resume.summary}\n\n`;
    }
    if (resume.experience && Array.isArray(resume.experience)) {
      formatted += 'EXPERIENCE\n';
      resume.experience.forEach((exp: any) => {
        if (exp.title) formatted += `${exp.title}\n`;
        if (exp.company) formatted += `${exp.company}\n`;
        if (exp.bullets && Array.isArray(exp.bullets)) {
          exp.bullets.forEach((bullet: string) => {
            formatted += `• ${bullet}\n`;
          });
        }
        formatted += '\n';
      });
    }
    if (resume.skills && Array.isArray(resume.skills)) {
      formatted += `SKILLS\n${resume.skills.join(', ')}\n`;
    }
    return formatted;
  };

  const tailoredText = formatResume(tailoredResume);

  // Initialize edited text when in tailored mode
  useEffect(() => {
    if (viewMode === 'tailored' && !editedText) {
      setEditedText(tailoredText);
    } else if (viewMode !== 'tailored') {
      // Reset when switching away from tailored mode
      setEditedText('');
      setHasChanges(false);
      setCalculatedScore(null);
    }
  }, [viewMode, tailoredText]);

  // Track changes when in tailored mode
  useEffect(() => {
    if (viewMode === 'tailored') {
      const hasChangesNow = editedText !== tailoredText;
      setHasChanges(hasChangesNow);
      
      // Reset calculated score when user makes new changes
      if (hasChangesNow && calculatedScore !== null) {
        setCalculatedScore(null);
      }
    }
  }, [editedText, viewMode, tailoredText, calculatedScore]);

  const handleApplyChanges = async () => {
    if (!jobId || !hasChanges) return;

    try {
      const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
      const response = await fetch(`${API_BASE_URL}/jobs/${jobId}/update-resume`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          edited_text: editedText,
        }),
      });

      if (!response.ok) {
        throw new Error('Failed to apply changes');
      }

      const data = await response.json();
      setHasChanges(false);
      setCalculatedScore(null); // Clear calculated score after applying
      
      // Update the edited text to reflect the saved version
      if (data.updated_resume) {
        const updatedText = formatResume(data.updated_resume);
        setEditedText(updatedText);
      }
      
      if (onResumeUpdate) {
        onResumeUpdate(data.updated_resume);
      }

      // Show success message
      toast.success('Changes applied successfully! The resume has been updated.');
    } catch (error) {
      console.error('Failed to apply changes:', error);
      toast.error('Failed to apply changes. Please try again.');
    }
  };

  const handleResetChanges = () => {
    setEditedText(tailoredText);
    setHasChanges(false);
    setCalculatedScore(null);
  };

  const handleCalculateATS = async () => {
    if (!jobId || !hasChanges || !editedText.trim()) return;

    setIsCalculating(true);
    setCalculatedScore(null);

    try {
      const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
      const response = await fetch(`${API_BASE_URL}/jobs/${jobId}/calculate-ats`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          edited_text: editedText,
        }),
      });

      if (!response.ok) {
        throw new Error('Failed to calculate ATS score');
      }

      const data = await response.json();
      setCalculatedScore(data.score);
      toast.success(`New ATS Score: ${data.score} (${data.score >= (currentATSScore || 0) ? '+' : ''}${data.score - (currentATSScore || 0)} points)`);
    } catch (error) {
      console.error('Failed to calculate ATS score:', error);
      toast.error('Failed to calculate ATS score. Please try again.');
    } finally {
      setIsCalculating(false);
    }
  };

  return (
    <div className="bg-white rounded-lg shadow-md p-6">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-2xl font-bold text-gray-900">Resume Preview</h2>
        <div className="flex items-center gap-2">
          {/* View Mode Buttons */}
          {originalResume && (
            <>
              <button
                onClick={() => setViewMode('original')}
                className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
                  viewMode === 'original'
                    ? 'bg-blue-600 text-white'
                    : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                }`}
              >
                Original
              </button>
              <button
                onClick={() => setViewMode('compare')}
                className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
                  viewMode === 'compare'
                    ? 'bg-blue-600 text-white'
                    : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                }`}
              >
                Compare
              </button>
            </>
          )}
          <button
            onClick={() => setViewMode('tailored')}
            className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
              viewMode === 'tailored'
                ? 'bg-blue-600 text-white'
                : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
            }`}
          >
            Tailored
          </button>
        </div>
      </div>

      <div className="border border-gray-300 rounded-lg p-6 bg-gray-50 min-h-[400px]">
        {viewMode === 'tailored' ? (
          <textarea
            ref={textareaRef}
            value={editedText}
            onChange={(e) => setEditedText(e.target.value)}
            className="w-full h-full min-h-[400px] p-4 text-sm text-gray-800 whitespace-pre-wrap font-sans border-none bg-white rounded resize-none focus:outline-none focus:ring-2 focus:ring-blue-500"
            placeholder="Edit your resume here. You can copy-paste suggestions from the chat..."
            onMouseUp={() => {
              if (onTextSelect) {
                const selection = window.getSelection();
                const selectedText = selection?.toString().trim();
                if (selectedText && selectedText.length > 0) {
                  onTextSelect(selectedText);
                }
              }
            }}
          />
        ) : viewMode === 'compare' && originalResume ? (
          <div className="grid md:grid-cols-2 gap-4">
            <div>
              <h3 className="font-semibold text-gray-700 mb-2">Original</h3>
              <pre 
                className="text-sm text-gray-800 whitespace-pre-wrap font-sans select-text cursor-text"
                onMouseUp={() => {
                  if (onTextSelect) {
                    const selection = window.getSelection();
                    const selectedText = selection?.toString().trim();
                    if (selectedText && selectedText.length > 0) {
                      onTextSelect(selectedText);
                    }
                  }
                }}
              >
                {originalResume}
              </pre>
            </div>
            <div>
              <h3 className="font-semibold text-gray-700 mb-2">Tailored</h3>
              <pre 
                className="text-sm text-gray-800 whitespace-pre-wrap font-sans select-text cursor-text"
                onMouseUp={() => {
                  if (onTextSelect) {
                    const selection = window.getSelection();
                    const selectedText = selection?.toString().trim();
                    if (selectedText && selectedText.length > 0) {
                      onTextSelect(selectedText);
                    }
                  }
                }}
              >
                {tailoredText}
              </pre>
            </div>
          </div>
        ) : (
          <pre 
            className="text-sm text-gray-800 whitespace-pre-wrap font-sans select-text cursor-text"
            onMouseUp={() => {
              if (onTextSelect) {
                const selection = window.getSelection();
                const selectedText = selection?.toString().trim();
                if (selectedText && selectedText.length > 0) {
                  onTextSelect(selectedText);
                }
              }
            }}
          >
            {viewMode === 'original' && originalResume ? originalResume : tailoredText}
          </pre>
        )}
      </div>
      
      {/* Action Buttons - Outside the preview area */}
      {viewMode === 'tailored' && jobId && (
        <div className="mt-4 space-y-3">
          <div className="flex items-center gap-3">
            <button
              onClick={handleCalculateATS}
              disabled={!hasChanges || isCalculating}
              className="px-6 py-2 bg-purple-500 text-white rounded-md text-sm font-medium hover:bg-purple-600 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors flex items-center gap-2"
            >
              {isCalculating ? (
                <>
                  <svg className="animate-spin h-4 w-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                  Calculating...
                </>
              ) : (
                <>
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                  </svg>
                  Calculate ATS Score
                </>
              )}
            </button>
            <button
              onClick={handleApplyChanges}
              disabled={!hasChanges}
              className="px-6 py-2 bg-blue-500 text-white rounded-md text-sm font-medium hover:bg-blue-600 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors"
            >
              Apply Changes
            </button>
            {hasChanges && (
              <button
                onClick={handleResetChanges}
                className="px-4 py-2 bg-gray-500 text-white rounded-md text-sm font-medium hover:bg-gray-600 transition-colors"
              >
                Reset
              </button>
            )}
          </div>
          
          <div className="text-xs text-gray-500">
            💡 Tip: Copy suggestions from the chat and paste them directly into the resume preview above. Use "Calculate ATS Score" to preview the impact before applying changes.
          </div>
          
          {calculatedScore !== null && currentATSScore !== undefined && (
            <div className={`p-3 rounded-lg border-2 ${
              calculatedScore >= currentATSScore 
                ? 'bg-green-50 border-green-200' 
                : 'bg-yellow-50 border-yellow-200'
            }`}>
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-semibold text-gray-700">Calculated ATS Score</p>
                  <p className="text-xs text-gray-600">
                    {calculatedScore >= currentATSScore ? '✓ Improved!' : '⚠ Score decreased'}
                  </p>
                </div>
                <div className="text-right">
                  <p className={`text-2xl font-bold ${
                    calculatedScore >= currentATSScore ? 'text-green-600' : 'text-yellow-600'
                  }`}>
                    {calculatedScore}
                  </p>
                  <p className="text-xs text-gray-500">
                    {calculatedScore >= currentATSScore ? '+' : ''}{calculatedScore - currentATSScore} points
                  </p>
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default ResumePreview;

