import React from 'react';

interface ATSScoreCardProps {
  beforeScore: number;
  afterScore: number;
  beforeDetails?: any;
  afterDetails?: any;
}

const ATSScoreCard: React.FC<ATSScoreCardProps> = ({
  beforeScore,
  afterScore,
  beforeDetails,
  afterDetails,
}) => {
  const improvement = afterScore - beforeScore;
  const improvementPercent = beforeScore > 0 ? ((improvement / beforeScore) * 100).toFixed(1) : 0;

  const getScoreColor = (score: number) => {
    if (score >= 80) return 'text-green-600';
    if (score >= 60) return 'text-yellow-600';
    return 'text-red-600';
  };

  const getScoreBgColor = (score: number) => {
    if (score >= 80) return 'bg-green-100';
    if (score >= 60) return 'bg-yellow-100';
    return 'bg-red-100';
  };

  return (
    <div className="bg-white rounded-lg shadow-md p-6">
      <h2 className="text-2xl font-bold text-gray-900 mb-6">ATS Score Comparison</h2>
      
      <div className="grid md:grid-cols-2 gap-6">
        {/* Before Score */}
        <div className="text-center">
          <p className="text-sm font-medium text-gray-600 mb-2">Before Optimization</p>
          <div className={`inline-flex items-center justify-center w-32 h-32 rounded-full ${getScoreBgColor(beforeScore)} mb-4`}>
            <span className={`text-4xl font-bold ${getScoreColor(beforeScore)}`}>
              {beforeScore}
            </span>
          </div>
          <p className="text-xs text-gray-500">ATS Match Score</p>
        </div>

        {/* After Score */}
        <div className="text-center">
          <p className="text-sm font-medium text-gray-600 mb-2">After Optimization</p>
          <div className={`inline-flex items-center justify-center w-32 h-32 rounded-full ${getScoreBgColor(afterScore)} mb-4`}>
            <span className={`text-4xl font-bold ${getScoreColor(afterScore)}`}>
              {afterScore}
            </span>
          </div>
          <p className="text-xs text-gray-500">ATS Match Score</p>
        </div>
      </div>

      {/* Improvement */}
      <div className="mt-6 pt-6 border-t border-gray-200 text-center">
        <div className="inline-flex items-center gap-2 px-4 py-2 bg-blue-50 rounded-full">
          <svg className="h-5 w-5 text-blue-600" fill="currentColor" viewBox="0 0 20 20">
            <path
              fillRule="evenodd"
              d="M5.293 9.707a1 1 0 010-1.414l4-4a1 1 0 011.414 0l4 4a1 1 0 01-1.414 1.414L11 7.414V15a1 1 0 11-2 0V7.414L6.707 9.707a1 1 0 01-1.414 0z"
              clipRule="evenodd"
            />
          </svg>
          <span className="text-lg font-bold text-blue-600">
            +{improvement} points ({improvementPercent}% improvement)
          </span>
        </div>
      </div>

      {/* Score Breakdown */}
      {(beforeDetails || afterDetails) && (
        <div className="mt-6 pt-6 border-t border-gray-200">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Score Breakdown</h3>
          <div className="grid md:grid-cols-2 gap-4">
            {beforeDetails && (
              <div>
                <p className="text-sm font-medium text-gray-700 mb-2">Before</p>
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-gray-600">Keywords Matched:</span>
                    <span className="font-medium">{beforeDetails.keywords_matched || 0}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600">Missing Keywords:</span>
                    <span className="font-medium">{beforeDetails.missing_keywords?.length || 0}</span>
                  </div>
                </div>
              </div>
            )}
            {afterDetails && (
              <div>
                <p className="text-sm font-medium text-gray-700 mb-2">After</p>
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-gray-600">Keywords Matched:</span>
                    <span className="font-medium text-green-600">{afterDetails.keywords_matched || 0}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600">Missing Keywords:</span>
                    <span className="font-medium text-green-600">{afterDetails.missing_keywords?.length || 0}</span>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default ATSScoreCard;

