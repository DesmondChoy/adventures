
import React, { useEffect, useRef, useState } from 'react';
import { CheckCircle, XCircle, Info } from 'lucide-react';

export interface QuestionData {
  question: string;
  userAnswer: string;
  isCorrect: boolean;
  correctAnswer?: string;
  explanation: string;
}

interface EducationalCardProps {
  data: QuestionData;
  index: number;
  delay?: number;
}

const EducationalCard: React.FC<EducationalCardProps> = ({ 
  data, 
  index,
  delay = 0 
}) => {
  const [expanded, setExpanded] = useState(false);
  const [visible, setVisible] = useState(false);
  const cardRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setTimeout(() => {
            setVisible(true);
          }, delay);
        }
      },
      { threshold: 0.1 }
    );

    if (cardRef.current) {
      observer.observe(cardRef.current);
    }

    return () => {
      if (cardRef.current) {
        observer.unobserve(cardRef.current);
      }
    };
  }, [delay]);

  return (
    <div 
      ref={cardRef}
      className={`educational-card ${data.isCorrect ? 'correct' : 'incorrect'} shadow-md mb-6 ${visible ? 'opacity-100 animate-scale-in' : 'opacity-0'}`}
      style={{ transitionDelay: `${delay}ms` }}
    >
      <div className="flex items-start gap-3">
        <div className={`flex-shrink-0 rounded-full ${data.isCorrect ? 'bg-green-100' : 'bg-red-100'} p-2 mt-1`}>
          {data.isCorrect ? (
            <CheckCircle className="h-5 w-5 text-green-600" />
          ) : (
            <XCircle className="h-5 w-5 text-red-500" />
          )}
        </div>
        
        <div className="flex-1">
          <span className="inline-block rounded-full bg-odyssey-lavender/10 px-2 py-1 text-xs font-medium text-odyssey-lavender mb-2">
            Question {index + 1}
          </span>
          <h4 className="text-base font-medium mb-2">{data.question}</h4>
          
          <div className="mb-3">
            <div className="text-sm text-gray-700">
              <span className="font-medium">Your answer: </span>
              <span className={data.isCorrect ? 'text-green-600' : 'text-red-500'}>
                {data.userAnswer}
              </span>
            </div>
            
            {!data.isCorrect && data.correctAnswer && (
              <div className="text-sm text-gray-700 mt-1">
                <span className="font-medium">Correct answer: </span>
                <span className="text-green-600">{data.correctAnswer}</span>
              </div>
            )}
          </div>
          
          <div 
            className={`transition-all duration-300 ${expanded ? 'max-h-48' : 'max-h-0 overflow-hidden'}`}
          >
            <div className="p-3 bg-white/50 rounded-lg border border-gray-100 mt-2">
              <div className="flex items-start gap-2">
                <Info className="h-4 w-4 text-odyssey-blue mt-0.5 flex-shrink-0" />
                <p className="text-sm text-gray-600">{data.explanation}</p>
              </div>
            </div>
          </div>
          
          <button
            onClick={() => setExpanded(!expanded)}
            className="text-sm text-odyssey-blue hover:text-odyssey-purple transition-colors mt-2"
          >
            {expanded ? 'Hide explanation' : 'Show explanation'}
          </button>
        </div>
      </div>
    </div>
  );
};

export default EducationalCard;
