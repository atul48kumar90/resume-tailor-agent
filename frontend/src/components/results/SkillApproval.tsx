import React, { useState } from 'react';
import toast from 'react-hot-toast';
import { useQueryClient } from '@tanstack/react-query';
import { approveSkills } from '../../services/api';

interface SkillApprovalProps {
  pendingSkills: string[];
  jobId: string;
  onApprovalComplete: () => void;
}

const SkillApproval: React.FC<SkillApprovalProps> = ({ pendingSkills, jobId, onApprovalComplete }) => {
  const queryClient = useQueryClient();
  const [selectedSkills, setSelectedSkills] = useState<Set<string>>(new Set());
  const [isSubmitting, setIsSubmitting] = useState(false);

  const toggleSkill = (skill: string) => {
    const newSelected = new Set(selectedSkills);
    if (newSelected.has(skill)) {
      newSelected.delete(skill);
    } else {
      newSelected.add(skill);
    }
    setSelectedSkills(newSelected);
  };

  const handleSubmit = async () => {
    if (selectedSkills.size === 0) {
      toast.error('Please select at least one skill to approve');
      return;
    }

    setIsSubmitting(true);
    try {
      await approveSkills(jobId, Array.from(selectedSkills));
      toast.success('Skills approved! Resume is being regenerated...');
      // Invalidate all related queries to force refetch
      queryClient.invalidateQueries({ queryKey: ['jobStatus', jobId] });
      queryClient.invalidateQueries({ queryKey: ['skillGap', jobId] });
      queryClient.invalidateQueries({ queryKey: ['atsCompare', jobId] });
      // Wait a bit for backend to update, then refetch
      setTimeout(() => {
        queryClient.refetchQueries({ queryKey: ['jobStatus', jobId] });
        queryClient.refetchQueries({ queryKey: ['skillGap', jobId] });
        queryClient.refetchQueries({ queryKey: ['atsCompare', jobId] });
      }, 500);
      onApprovalComplete();
    } catch (error) {
      toast.error('Failed to approve skills. Please try again.');
      console.error('Error approving skills:', error);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleSkip = () => {
    // Skip approval - use current resume as-is
    onApprovalComplete();
  };

  if (pendingSkills.length === 0) {
    return null;
  }

  return (
    <div className="bg-white rounded-lg shadow-md p-6 mb-6">
      <h2 className="text-2xl font-bold text-gray-900 mb-4">Review Suggested Skills</h2>
      <p className="text-gray-600 mb-6">
        The following skills were suggested to improve your ATS score. Select the skills you'd like to add to your resume.
        Only select skills you actually have experience with.
      </p>

      <div className="mb-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-3">
          Suggested Skills ({selectedSkills.size} selected)
        </h3>
        <div className="flex flex-wrap gap-3">
          {pendingSkills.map((skill) => {
            const isSelected = selectedSkills.has(skill);
            return (
              <button
                key={skill}
                onClick={() => toggleSkill(skill)}
                className={`px-4 py-2 rounded-lg font-medium transition-all duration-200 ${
                  isSelected
                    ? 'bg-blue-600 text-white shadow-md transform scale-105'
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                }`}
                type="button"
              >
                {skill}
              </button>
            );
          })}
        </div>
      </div>

      <div className="flex gap-4">
        <button
          onClick={handleSubmit}
          disabled={isSubmitting || selectedSkills.size === 0}
          className={`px-6 py-3 rounded-lg font-medium transition-colors ${
            isSubmitting || selectedSkills.size === 0
              ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
              : 'bg-blue-600 text-white hover:bg-blue-700'
          }`}
        >
          {isSubmitting ? 'Processing...' : `Apply ${selectedSkills.size} Skill${selectedSkills.size !== 1 ? 's' : ''}`}
        </button>
        <button
          onClick={handleSkip}
          disabled={isSubmitting}
          className="px-6 py-3 rounded-lg font-medium bg-gray-200 text-gray-700 hover:bg-gray-300 transition-colors disabled:opacity-50"
        >
          Skip (Use Current Resume)
        </button>
      </div>
    </div>
  );
};

export default SkillApproval;

