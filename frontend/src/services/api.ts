const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

// Types
export interface JobStatus {
  job_id: string;
  status: 'queued' | 'processing' | 'completed' | 'finished' | 'failed' | 'pending';
  result?: any;
  error?: string;
  queue_position?: number;
}

export interface ATSCompare {
  before: {
    score: number;
    keywords_matched: number;
    missing_keywords: string[];
  };
  after: {
    score: number;
    keywords_matched: number;
    missing_keywords: string[];
  };
}

// API Functions
export const tailorResume = async (formData: FormData): Promise<{ job_id: string }> => {
  const response = await fetch(`${API_BASE_URL}/tailor`, {
    method: 'POST',
    body: formData,
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to tailor resume');
  }

  return response.json();
};

export const getJobStatus = async (jobId: string): Promise<JobStatus> => {
  const response = await fetch(`${API_BASE_URL}/jobs/${jobId}`);

  if (!response.ok) {
    throw new Error('Failed to get job status');
  }

  return response.json();
};

export const getATSCompare = async (jobId: string): Promise<ATSCompare> => {
  const response = await fetch(`${API_BASE_URL}/ats/compare/${jobId}`);

  if (!response.ok) {
    throw new Error('Failed to get ATS comparison');
  }

  return response.json();
};

export const getSkillGap = async (jobId: string): Promise<any> => {
  const response = await fetch(`${API_BASE_URL}/ats/compare/${jobId}/skill-gap`);

  if (!response.ok) {
    throw new Error('Failed to get skill gap analysis');
  }

  return response.json();
};

export const approveSkills = async (jobId: string, approvedSkills: string[]): Promise<any> => {
  const response = await fetch(`${API_BASE_URL}/jobs/${jobId}/approve-skills`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      approved_skills: approvedSkills,
    }),
  });

  if (!response.ok) {
    throw new Error('Failed to approve skills');
  }

  return response.json();
};

export const downloadResume = async (
  resumeData: any,
  format: 'docx' | 'pdf' | 'txt' = 'docx'
): Promise<Blob> => {
  const response = await fetch(`${API_BASE_URL}/ats/download?format=${format}`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(resumeData),
  });

  if (!response.ok) {
    throw new Error('Failed to download resume');
  }

  return response.blob();
};

export const downloadResumeZip = async (resumeData: any): Promise<Blob> => {
  const response = await fetch(`${API_BASE_URL}/ats/download/zip`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(resumeData),
  });

  if (!response.ok) {
    throw new Error('Failed to download resume bundle');
  }

  return response.blob();
};

/**
 * Download tailored resume from a completed job by job ID.
 * This is the preferred method as it uses the job result directly.
 */
export const downloadJobResume = async (
  jobId: string,
  format: 'docx' | 'pdf' | 'txt' | 'zip' = 'docx'
): Promise<Blob> => {
  const response = await fetch(`${API_BASE_URL}/jobs/${jobId}/download?format=${format}`, {
    method: 'GET',
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Failed to download resume' }));
    throw new Error(error.detail || 'Failed to download resume');
  }

  return response.blob();
};

export const getResumes = async (userId?: string): Promise<any[]> => {
  const url = userId
    ? `${API_BASE_URL}/resumes?user_id=${userId}`
    : `${API_BASE_URL}/resumes`;
  const response = await fetch(url);

  if (!response.ok) {
    throw new Error('Failed to get resumes');
  }

  return response.json();
};

export const createResume = async (data: {
  title: string;
  tags?: string[];
  user_id?: string;
}): Promise<any> => {
  const formData = new FormData();
  formData.append('title', data.title);
  if (data.tags) {
    data.tags.forEach((tag) => formData.append('tags', tag));
  }
  if (data.user_id) {
    formData.append('user_id', data.user_id);
  }

  const response = await fetch(`${API_BASE_URL}/resumes`, {
    method: 'POST',
    body: formData,
  });

  if (!response.ok) {
    throw new Error('Failed to create resume');
  }

  return response.json();
};

export const getTemplates = async (): Promise<any[]> => {
  const response = await fetch(`${API_BASE_URL}/ats/templates`);

  if (!response.ok) {
    throw new Error('Failed to get templates');
  }

  return response.json();
};

export const batchProcess = async (formData: FormData): Promise<any> => {
  const response = await fetch(`${API_BASE_URL}/ats/batch`, {
    method: 'POST',
    body: formData,
  });

  if (!response.ok) {
    throw new Error('Failed to process batch');
  }

  return response.json();
};

// Chat API
export interface ChatRequest {
  message: string;
  context?: string;
  job_id?: string;
  chat_history?: Array<{ role: string; content: string }>;
}

export interface ChatResponse {
  response: string;
  suggestions?: string[];
}

export const sendChatMessage = async (request: ChatRequest): Promise<ChatResponse> => {
  const response = await fetch(`${API_BASE_URL}/chat/resume-edit`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to send chat message');
  }

  return response.json();
};

export const applySuggestion = async (
  jobId: string,
  section: string,
  originalText: string,
  suggestedText: string
) => {
  const response = await fetch(`${API_BASE_URL}/chat/apply-suggestion`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      job_id: jobId,
      section,
      original_text: originalText,
      suggested_text: suggestedText,
    }),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to apply suggestion');
  }

  return response.json();
};

