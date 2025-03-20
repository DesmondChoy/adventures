
import React, { useEffect, useRef, useState } from 'react';
import { ScrollArea } from '@/components/ui/scroll-area';
import { BookOpen, ChevronDown, ChevronUp } from 'lucide-react';

interface ChapterCardProps {
  number: number;
  title: string;
  summary: string;
  delay?: number;
}

const ChapterCard: React.FC<ChapterCardProps> = ({ 
  number, 
  title, 
  summary,
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
      className={`chapter-card mb-6 ml-8 ${visible ? 'opacity-100 animate-fade-in-up' : 'opacity-0'}`}
      style={{ transitionDelay: `${delay}ms` }}
    >
      <div className="absolute -left-8 flex h-8 w-8 items-center justify-center rounded-full border border-odyssey-teal bg-white z-10">
        <BookOpen className="h-4 w-4 text-odyssey-purple" />
      </div>
      
      <div className="mb-2 flex items-center justify-between">
        <div>
          <span className="inline-block rounded-full bg-odyssey-teal/10 px-2 py-1 text-xs font-medium text-odyssey-teal">
            Chapter {number}
          </span>
          <h3 className="mt-2 text-lg font-medium">{title}</h3>
        </div>
        <button 
          onClick={() => setExpanded(!expanded)}
          className="rounded-full p-2 hover:bg-gray-100 transition-colors"
          aria-label={expanded ? "Collapse chapter" : "Expand chapter"}
        >
          {expanded ? (
            <ChevronUp className="h-5 w-5 text-gray-500" />
          ) : (
            <ChevronDown className="h-5 w-5 text-gray-500" />
          )}
        </button>
      </div>
      
      <div className={`transition-all duration-300 ease-in-out overflow-hidden ${expanded ? 'max-h-96' : 'max-h-24'}`}>
        <ScrollArea className="h-full pr-4">
          <p className="text-gray-600 leading-relaxed">{summary}</p>
        </ScrollArea>
      </div>
      
      {!expanded && (
        <div className="absolute bottom-0 left-0 w-full h-16 bg-gradient-to-t from-white to-transparent pointer-events-none" />
      )}
    </div>
  );
};

export default ChapterCard;
