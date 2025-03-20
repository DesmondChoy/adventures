import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { 
  Award, 
  BookOpen, 
  Brain,
  ChevronDown, 
  Clock, 
  MapPin, 
  PartyPopper, 
  Sparkles, 
  Trophy 
} from 'lucide-react';

import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Separator } from '@/components/ui/separator';
import { ScrollArea } from '@/components/ui/scroll-area';

import Confetti from '@/components/adventure/Confetti';
import ChapterCard from '@/components/adventure/ChapterCard';
import EducationalCard from '@/components/adventure/EducationalCard';
import StatisticCard from '@/components/adventure/StatisticCard';
import { QuestionData } from '@/components/adventure/EducationalCard';
import { AdventureSummaryData } from '@/lib/types';

// Default data to use if fetch fails
const defaultData: AdventureSummaryData = {
  chapterSummaries: [
    {
      number: 1,
      title: "Chapter 1: The Mysterious Carnival",
      summary: "Drawn by whispers of the Twisting Tumble Tents carnival, Leo, a curious child known for their bright red sneakers, discovered the carnival was indeed real. The air vibrated with tantalizing scents and calliope music, beckoning Leo closer. Overcome with excitement, Leo stepped through a gap in the fence, where shifting tents and glowing performers created a surreal atmosphere. Before plunging deeper into the carnival alone, Leo noticed a small animal hiding behind juggling pins. Leo decided to enlist a wise old owl as their companion, hoping its ancient riddles might unlock hidden paths and reveal the carnival's deepest mysteries.",
      chapterType: "STORY"
    },
    {
      number: 2,
      title: "Chapter 2: Whispers in the Wind",
      summary: "Leo and the wise owl ventured deeper into the mysterious carnival, where colorful tents swayed in an impossible breeze. The owl shared ancient knowledge about the carnival's history as they encountered strange performers who seemed to float inches above the ground. Leo decided to follow the sound of ethereal music, leading them to a hidden courtyard with a magnificent carousel.",
      chapterType: "STORY"
    },
    {
      number: 3,
      title: "Chapter 3: The Carousel of Dreams",
      summary: "The carousel glowed with an otherworldly light, each carved animal seeming to watch Leo with curious eyes. When offered a choice of mounts, Leo selected a magnificent phoenix with feathers that shifted through every color of flame. As the carousel began to turn, Leo and the owl were transported to a realm of living stories, where Leo's imagination influenced the very landscape around them.",
      chapterType: "STORY"
    }
  ],
  educationalQuestions: [
    {
      question: "Why did Stamford Raffles choose Singapore as a trading port in 1819?",
      userAnswer: "Singapore had a strategic location between the Indian Ocean and South China Sea.",
      isCorrect: true,
      explanation: "Singapore's location at the southern tip of the Malay Peninsula made it perfect for controlling trade routes between China, India, and Europe. There wasn't a large settlement when Raffles arrived - just a small fishing village - and Singapore didn't have valuable gold mines."
    },
    {
      question: "How did the opening of the Suez Canal in 1869 affect Singapore?",
      userAnswer: "It made Singapore less important as ships could bypass it completely.",
      isCorrect: false,
      correctAnswer: "It made Singapore more important as ships could travel between Asia and Europe faster.",
      explanation: "The Suez Canal shortened the journey between Europe and Asia by thousands of miles, bringing more ships through the Strait of Malacca where Singapore is located. This increased trade and Singapore's importance as a port, rather than making it less important or having no effect."
    }
  ],
  statistics: {
    chaptersCompleted: 10,
    questionsAnswered: 5,
    timeSpent: "45 mins",
    correctAnswers: 4
  }
};

const AdventureSummary: React.FC = () => {
  const [showConfetti, setShowConfetti] = useState(false);
  const [contentVisible, setContentVisible] = useState(false);
  const [summaryData, setSummaryData] = useState<AdventureSummaryData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  useEffect(() => {
    // Trigger confetti animation when component mounts
    setShowConfetti(true);
    
    // Delay the appearance of content for a better visual effect
    const timer = setTimeout(() => {
      setContentVisible(true);
    }, 800);
    
    // Fetch the summary data
    const fetchData = async () => {
      try {
        // Try to fetch from the API endpoint
        const response = await fetch('/adventure/api/adventure-summary');
        if (!response.ok) {
          throw new Error(`Failed to fetch data: ${response.status} ${response.statusText}`);
        }
        const data = await response.json();
        setSummaryData(data);
      } catch (err) {
        console.error('Error fetching summary data:', err);
        setError('Failed to load adventure summary data. Using default data instead.');
        // Use default data if fetch fails
        setSummaryData(defaultData);
      } finally {
        setLoading(false);
      }
    };
    
    fetchData();
    
    return () => clearTimeout(timer);
  }, []);

  // If still loading, show a loading indicator
  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-b from-blue-50 to-purple-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin h-12 w-12 border-4 border-odyssey-blue border-t-transparent rounded-full mx-auto mb-4"></div>
          <p className="text-gray-600">Loading your adventure summary...</p>
        </div>
      </div>
    );
  }

  // If there's an error and no data, show an error message
  if (error && !summaryData) {
    return (
      <div className="min-h-screen bg-gradient-to-b from-blue-50 to-purple-50 flex items-center justify-center">
        <div className="text-center max-w-md p-6 bg-white rounded-xl shadow-md">
          <div className="text-red-500 mb-4">
            <svg xmlns="http://www.w3.org/2000/svg" className="h-12 w-12 mx-auto" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
          </div>
          <h2 className="text-xl font-bold mb-2">Error Loading Data</h2>
          <p className="text-gray-600 mb-4">{error}</p>
          <Button 
            variant="outline" 
            onClick={() => window.location.reload()}
          >
            Try Again
          </Button>
        </div>
      </div>
    );
  }

  // If we have data, render the summary
  const data = summaryData || defaultData;

  return (
    <div className="min-h-screen bg-gradient-to-b from-blue-50 to-purple-50 overflow-hidden">
      {showConfetti && <Confetti count={100} duration={5000} />}
      
      <div className="container mx-auto px-4 py-16 max-w-5xl">
        {/* Header Section */}
        <div className={`text-center mb-12 transition-opacity duration-700 ${contentVisible ? 'opacity-100' : 'opacity-0'}`}>
          <div className="inline-block animate-float mb-4">
            <div className="bg-white rounded-full p-4 shadow-md">
              <PartyPopper className="h-12 w-12 text-odyssey-pink" />
            </div>
          </div>
          
          <h1 className="text-4xl md:text-5xl font-bold mb-4 bg-clip-text text-transparent bg-gradient-to-r from-odyssey-blue via-odyssey-purple to-odyssey-pink">
            Adventure Complete!
          </h1>
          
          <p className="text-gray-600 text-lg max-w-2xl mx-auto">
            Congratulations on completing your learning odyssey! Let's revisit your journey and celebrate all that you've learned.
          </p>
        </div>
        
        {/* Statistics Section */}
        <div className={`grid grid-cols-1 md:grid-cols-3 gap-4 mb-12 transition-opacity duration-700 ${contentVisible ? 'opacity-100' : 'opacity-0'}`}>
          <StatisticCard 
            title="Chapters Completed" 
            value={data.statistics.chaptersCompleted.toString()} 
            icon={<BookOpen className="h-6 w-6 text-odyssey-blue" />}
            delay={200}
          />
          <StatisticCard 
            title="Questions Answered" 
            value={data.statistics.questionsAnswered.toString()} 
            icon={<Brain className="h-6 w-6 text-odyssey-purple" />}
            delay={400}
          />
          <StatisticCard 
            title="Time Spent" 
            value={data.statistics.timeSpent} 
            icon={<Clock className="h-6 w-6 text-odyssey-pink" />}
            delay={600}
          />
        </div>
        
        {/* Achievement Badge */}
        <Card className={`p-6 mb-12 glass-card text-center transition-opacity duration-700 ${contentVisible ? 'opacity-100' : 'opacity-0'}`}>
          <div className="flex justify-center mb-4">
            <div className="achievement-badge h-24 w-24 animate-pulse-soft">
              <Trophy className="h-12 w-12 text-white z-10 relative" />
            </div>
          </div>
          
          <h2 className="text-2xl font-bold mb-2">Adventure Master</h2>
          <p className="text-gray-600 mb-4">You've demonstrated curiosity, problem-solving, and a love for learning!</p>
          
          <div className="flex justify-center space-x-2">
            <div className="bg-odyssey-teal/10 text-odyssey-teal text-sm font-medium rounded-full px-3 py-1">
              Creative Thinker
            </div>
            <div className="bg-odyssey-purple/10 text-odyssey-purple text-sm font-medium rounded-full px-3 py-1">
              Knowledge Seeker
            </div>
            <div className="bg-odyssey-pink/10 text-odyssey-pink text-sm font-medium rounded-full px-3 py-1">
              Problem Solver
            </div>
          </div>
        </Card>
        
        {/* Journey Timeline Section */}
        <div className={`mb-12 transition-opacity duration-700 ${contentVisible ? 'opacity-100 delay-300' : 'opacity-0'}`}>
          <div className="flex items-center mb-6">
            <MapPin className="h-6 w-6 text-odyssey-teal mr-2" />
            <h2 className="text-2xl font-bold">Your Adventure Journey</h2>
          </div>
          
          <div className="relative pl-4">
            <div className="timeline-connector" />
            
            {data.chapterSummaries.map((chapter, index) => (
              <ChapterCard 
                key={chapter.number}
                number={chapter.number}
                title={chapter.title}
                summary={chapter.summary}
                delay={index * 150}
              />
            ))}
          </div>
        </div>
        
        {/* Educational Achievement Section */}
        <div className={`mb-12 transition-opacity duration-700 ${contentVisible ? 'opacity-100 delay-500' : 'opacity-0'}`}>
          <div className="flex items-center mb-6">
            <Sparkles className="h-6 w-6 text-odyssey-lavender mr-2" />
            <h2 className="text-2xl font-bold">Knowledge Gained</h2>
          </div>
          
          <div className="grid grid-cols-1 gap-6">
            {data.educationalQuestions.map((question, index) => (
              <EducationalCard 
                key={index}
                data={question}
                index={index}
                delay={index * 200}
              />
            ))}
          </div>
        </div>
        
        {/* Footer Section */}
        <div className={`text-center transition-opacity duration-700 ${contentVisible ? 'opacity-100 delay-700' : 'opacity-0'}`}>
          <Separator className="mb-8" />
          
          <div className="mb-6">
            <Award className="h-8 w-8 text-odyssey-yellow mx-auto mb-4" />
            <h2 className="text-2xl font-bold mb-2">Ready for Another Adventure?</h2>
            <p className="text-gray-600 mb-6">
              Your curiosity has led you through an amazing journey. What will you discover next?
            </p>
          </div>
          
          <div className="flex flex-col sm:flex-row justify-center gap-4">
            <Button 
              size="lg" 
              className="bg-gradient-to-r from-odyssey-blue to-odyssey-teal hover:opacity-90 transition-opacity"
            >
              <Link to="/">Start New Adventure</Link>
            </Button>
            <Button 
              variant="outline" 
              size="lg"
              className="border-odyssey-purple text-odyssey-purple hover:bg-odyssey-purple/5"
            >
              <Link to="/">Return Home</Link>
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default AdventureSummary;
