import React from 'react';

interface PersonaSelectorProps {
  value: string;
  onChange: (value: string) => void;
}

const personas = [
  { id: 'general', label: 'General', description: 'Standard resume format' },
  { id: 'technical', label: 'Technical', description: 'Emphasize technical skills' },
  { id: 'executive', label: 'Executive', description: 'Leadership-focused' },
  { id: 'creative', label: 'Creative', description: 'Creative industries' },
];

const PersonaSelector: React.FC<PersonaSelectorProps> = ({ value, onChange }) => {
  return (
    <div>
      <label className="block text-sm font-medium text-gray-700 mb-2">
        Recruiter Persona
      </label>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {personas.map((persona) => (
          <button
            key={persona.id}
            type="button"
            onClick={() => onChange(persona.id)}
            className={`p-4 border-2 rounded-lg text-left transition-colors ${
              value === persona.id
                ? 'border-blue-500 bg-blue-50'
                : 'border-gray-300 hover:border-gray-400'
            }`}
          >
            <div className="flex items-center gap-2 mb-1">
              <div
                className={`w-4 h-4 rounded-full border-2 flex items-center justify-center ${
                  value === persona.id
                    ? 'border-blue-500 bg-blue-500'
                    : 'border-gray-300'
                }`}
              >
                {value === persona.id && (
                  <div className="w-2 h-2 rounded-full bg-white" />
                )}
              </div>
              <span className="font-medium text-gray-900">{persona.label}</span>
            </div>
            <p className="text-xs text-gray-500">{persona.description}</p>
          </button>
        ))}
      </div>
    </div>
  );
};

export default PersonaSelector;

